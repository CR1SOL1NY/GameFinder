"""Datos sintéticos: emulados por defecto; MongoDB real exige un destino aislado."""
import os
import uuid
os.environ['GAMEFINDER_TEST_MODE'] = '1'
os.environ['ENVIRONMENT'] = 'development'
os.environ['COOKIE_SECURE'] = 'false'
os.environ['COOKIE_SAMESITE'] = 'lax'
os.environ['CORS_ORIGINS'] = 'http://localhost:5173,http://127.0.0.1:5173'
if os.getenv('TEST_MONGODB_URI') and not os.environ['TEST_MONGODB_URI'].startswith(('mongodb://127.0.0.1:', 'mongodb://localhost:')):
    raise RuntimeError('TEST_MONGODB_URI debe apuntar a MongoDB local; nunca a Atlas')
os.environ['JWT_SECRET_KEY'] = 'clave-exclusiva-para-pruebas-aisladas-1234567890'
from pruebas_interfaz.mongodb_real import configurar_conexion_aplicacion
configurar_conexion_aplicacion()
import pytest_asyncio
import httpx
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient
from integracion_frontend.database import get_db, crear_indices
from integracion_frontend.limiter import limiter
from integracion_frontend.aplicacion import app
from pruebas_interfaz.mongodb_real import conectar_pruebas, limpiar_colecciones

@pytest_asyncio.fixture
async def env():
    real_uri = os.getenv('TEST_MONGODB_URI')
    isolated = os.getenv('GAMEFINDER_MONGODB_REAL') == '1'
    token = None
    if isolated:
        mongo_client, db, token = await conectar_pruebas()
        await limpiar_colecciones(db, token)
    elif real_uri:
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_client = AsyncIOMotorClient(real_uri, serverSelectionTimeoutMS=5000)
        await mongo_client.admin.command('ping')
        name = 'gamefinder_test_' + uuid.uuid4().hex
        db = mongo_client[name]
    else:
        mongo_client = None
        db = AsyncMongoMockClient()['gamefinder_tests']
    previous_limiter = limiter.enabled
    try:
        await crear_indices(db)
        tid = ObjectId(); gid = ObjectId(); gid2=ObjectId()
        await db.tiendas.insert_one({'_id':tid,'nombre':'Tienda de prueba (no real)'})
        await db.juegos.insert_many([
          {'_id':gid,'titulo':'Juego de prueba Alfa','generos':['RPG'],'plataformas':['PC'],'fechaLanzamiento':'2024-01-01','precios':[{'tiendaId':tid,'precio':15000,'moneda':'CLP'},{'tiendaId':tid,'precio':10,'moneda':'USD'}]},
          {'_id':gid2,'titulo':'Juego de prueba Beta','generos':['Aventura'],'plataformas':['PS5'],'precios':[]},
        ])
        app.dependency_overrides[get_db] = lambda: db
        limiter.enabled = False
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://testserver',headers={'Origin':'http://localhost:5173'}) as client:
          yield client,db,str(gid),str(gid2),str(tid)
    finally:
        app.dependency_overrides.clear()
        limiter.enabled = previous_limiter
        if mongo_client is not None:
            try:
                if isolated:
                    await limpiar_colecciones(db, token)
                else:
                    assert db.name.startswith('gamefinder_test_')
                    await mongo_client.drop_database(db.name)
            finally:
                mongo_client.close()

async def register(client,correo='ana@example.com'):
    r=await client.post('/usuarios/',json={'nombre':'Ana Prueba','correo':correo,'contrasena':'PruebaSegura123!'})
    assert r.status_code==201,r.text
    return r.json()

async def login(client,correo='ana@example.com'):
    r=await client.post('/usuarios/login',json={'correo':correo,'contrasena':'PruebaSegura123!'})
    assert r.status_code==200,r.text
    return r.json()
