"""Garantías que precisan un servidor MongoDB real, nunca simuladas con mongomock."""
import os
import pytest
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from pruebas_interfaz.conftest import register, login

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(
    os.getenv('GAMEFINDER_MONGODB_REAL') != '1' and not os.getenv('TEST_MONGODB_URI'),
    reason='Requiere MongoDB real para verificar conexiones e índices con collation')]


async def test_mongo_aplica_unicidad_de_correo_sin_distinguir_mayusculas(env):
    c, db, *_ = env
    await register(c)
    with pytest.raises(DuplicateKeyError):
        await db.usuarios.insert_one({'correo': 'ANA@EXAMPLE.COM', 'nombre': 'Duplicado sintético'})
    assert await db.usuarios.count_documents({}) == 1


async def test_deseados_y_sesiones_persisten_entre_conexiones(env):
    c, db, gid, *_ = env
    user = await register(c)
    await login(c)
    assert (await c.put(f"/usuarios/{user['_id']}/deseados/{gid}")).status_code == 200
    if os.getenv('GAMEFINDER_MONGODB_REAL') == '1':
        from app.database import db as application_db
        assert application_db.name == db.name
        health = await c.get('/health/db')
        assert health.status_code == 200 and health.json()['mongodb'] == 'conectado'
    from motor.motor_asyncio import AsyncIOMotorClient
    uri = os.getenv('MONGODB_PRUEBAS_URI') if os.getenv('GAMEFINDER_MONGODB_REAL') == '1' else os.environ['TEST_MONGODB_URI']
    another = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
    try:
        persisted = await another[db.name].usuarios.find_one({'_id': ObjectId(user['_id'])})
        assert persisted['listaDeseados'][0]['juegoId'] == ObjectId(gid)
        assert await another[db.name].sesiones.count_documents({'usuarioId': persisted['_id']}) == 1
    finally:
        another.close()
