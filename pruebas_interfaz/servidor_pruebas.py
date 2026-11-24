"""API HTTP exclusiva para las pruebas React. Persistencia EMULADA y descartable.
Nunca usar este módulo como entrypoint de producción.
"""
import os
import uuid
if os.getenv('GAMEFINDER_TEST_SERVER') != '1':
    raise RuntimeError('Este servidor solo se habilita explícitamente para pruebas')
os.environ['GAMEFINDER_TEST_MODE'] = '1'
os.environ['ENVIRONMENT'] = 'development'
os.environ['COOKIE_SECURE'] = 'false'
os.environ['COOKIE_SAMESITE'] = 'lax'
os.environ['CORS_ORIGINS'] = 'http://localhost:5173,http://127.0.0.1:5173'
if os.getenv('TEST_MONGODB_URI') and not os.environ['TEST_MONGODB_URI'].startswith(('mongodb://127.0.0.1:', 'mongodb://localhost:')):
    raise RuntimeError('TEST_MONGODB_URI debe apuntar a MongoDB local; nunca a Atlas')
os.environ['JWT_SECRET_KEY'] = 'clave-exclusiva-para-pruebas-http-1234567890'
os.environ['MONGO_URL'] = 'mongodb://127.0.0.1:27017/?directConnection=true'
os.environ.pop('MONGODB_URI', None)
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from mongomock_motor import AsyncMongoMockClient
from bson import ObjectId
from fastapi import FastAPI
from main_interfaz import app
from integracion_frontend.aplicacion import app as api_interfaz
from integracion_frontend.database import get_db, crear_indices
from integracion_frontend.limiter import limiter

if os.getenv('TEST_MONGODB_URI'):
    from motor.motor_asyncio import AsyncIOMotorClient
    mongo_client=AsyncIOMotorClient(os.environ['TEST_MONGODB_URI'],serverSelectionTimeoutMS=5000)
    db=mongo_client['gamefinder_test_http_'+uuid.uuid4().hex]
else:
    mongo_client=None
    db=AsyncMongoMockClient()['gamefinder_tests_http']
limiter.enabled=False
app.dependency_overrides[get_db]=lambda:db
api_interfaz.dependency_overrides[get_db]=lambda:db

async def reset():
    for name in await db.list_collection_names():
        await db[name].delete_many({})
    await crear_indices(db)
    # Cuenta administrativa exclusiva de esta base descartable, nunca del producto.
    import bcrypt
    await db.usuarios.insert_one({'nombre': 'Admin de pruebas', 'correo': 'admin-test@example.com', 'contrasenaHash': bcrypt.hashpw(b'ClaveSoloPruebas123!', bcrypt.gensalt(rounds=4)).decode(), 'rol': 'admin', 'listaDeseados': []})
    tid=ObjectId('000000000000000000000010');gid=ObjectId('000000000000000000000001')
    await db.tiendas.insert_one({'_id':tid,'nombre':'Tienda de prueba (datos sintéticos)'})
    stores_platforms = [
        {'_id': ObjectId('000000000000000000000011'), 'nombre': 'Tienda PC de prueba'},
        {'_id': ObjectId('000000000000000000000012'), 'nombre': 'Tienda PS5 de prueba'},
        {'_id': ObjectId('000000000000000000000013'), 'nombre': 'Tienda sin plataforma de prueba'},
        {'_id': ObjectId('000000000000000000000014'), 'nombre': 'Tienda USD de prueba'},
    ]
    await db.tiendas.insert_many(stores_platforms)
    await db.juegos.insert_one({
        '_id': ObjectId('000000000000000000000003'),
        'titulo': 'Juego de prueba Comparación', 'generos': ['Estrategia'],
        'plataformas': ['PC', 'PS5', 'Xbox'],
        'precios': [
            {'tiendaId': stores_platforms[0]['_id'], 'precio': 20000, 'moneda': 'CLP', 'plataforma': 'PC'},
            {'tiendaId': stores_platforms[1]['_id'], 'precio': 10000, 'moneda': 'CLP', 'plataforma': 'PS5'},
            {'tiendaId': stores_platforms[2]['_id'], 'precio': 5000, 'moneda': 'CLP'},
            {'tiendaId': stores_platforms[3]['_id'], 'precio': 10, 'moneda': 'USD', 'plataforma': 'PC'},
        ],
    })
    await db.juegos.insert_many([
        {
            '_id': gid, 'titulo': 'Juego de prueba Alfa',
            'descripcion': 'Descripción sintética de integración',
            'descripcionCorta': 'Resumen breve sintético de la ficha',
            'imagenFondo': 'https://example.com/fondo-sintetico.jpg',
            'caracteristicas': ['Exploración sintética de prueba', 'Combates sintéticos de prueba'],
            'requisitosSistema': {
                'plataforma': 'PC',
                'minimos': {'sistemaOperativo': 'SO mínimo de prueba', 'procesador': 'CPU mínima de prueba', 'memoria': 'Memoria mínima de prueba'},
                'recomendados': {'procesador': 'CPU recomendada de prueba', 'almacenamiento': 'Espacio recomendado de prueba'},
            },
            'generos': ['RPG'], 'plataformas': ['PC'],
            'fechaLanzamiento': datetime(2025, 1, 1, tzinfo=timezone.utc),
            'precios': [{'tiendaId': tid, 'precio': 15000, 'moneda': 'CLP', 'plataforma': 'PC'}],
        },
        {'_id': ObjectId('000000000000000000000002'), 'titulo': 'Juego de prueba Beta', 'generos': ['Aventura'], 'plataformas': ['PS5'], 'precios': []},
    ])

@asynccontextmanager
async def lifespan(application):
    if mongo_client is not None:
        await mongo_client.admin.command('ping')
    await reset()
    yield
    if mongo_client is not None:
        assert db.name.startswith('gamefinder_test_http_')
        await mongo_client.drop_database(db.name)
        mongo_client.close()
app.router.lifespan_context=lifespan

@api_interfaz.post('/__tests__/reset', include_in_schema=False)
async def reset_endpoint():
    await reset()
    return {'datos':'sintéticos y aislados'}
