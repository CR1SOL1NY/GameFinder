"""Protecciones del ejecutor real; las pruebas de guardas usan MongoDB emulado."""
import pytest
from mongomock_motor import AsyncMongoMockClient
from pruebas_interfaz.mongodb_real import (
    COLECCIONES, MARCADOR, validar_configuracion, reclamar, limpiar_colecciones, liberar,
)


@pytest.mark.parametrize('nombre', ['', 'GameFinder', 'gamefinder', 'admin', 'gamefinder_pruebas.otro', 'gamefinder_pruebas/otra'])
def test_rechaza_bases_ajenas(nombre):
    with pytest.raises(ValueError):
        validar_configuracion('mongodb://127.0.0.1:27028/', nombre)


@pytest.mark.parametrize('uri', [
    '', 'mongodb+srv://usuario:clave@cluster.example.org/',
    'mongodb+srv://usuario:clave@cluster.mongodb.net/GameFinder',
    'mongodb+srv://usuario:clave@cluster.mongodb.net/?tls=false',
    'mongodb+srv://usuario:clave@cluster.mongodb.net/?tlsInsecure=true',
    'mongodb+srv://usuario:clave@cluster.mongodb.net/?tlsAllowInvalidCertificates=true',
    'mongodb+srv://usuario:clave@cluster.mongodb.net/?tlsAllowInvalidHostnames=true',
    'mongodb://servidor-remoto.example.com:27017/',
    'mongodb://127.0.0.1:27028,servidor-remoto.example.com:27017/',
    'mongodb+srv://cluster.mongodb.net:27017/',
])
def test_rechaza_destinos_inseguros_sin_revelar_la_uri(uri):
    with pytest.raises(ValueError) as error:
        validar_configuracion(uri, 'gamefinder_pruebas')
    assert 'usuario:clave' not in str(error.value)


@pytest.mark.parametrize('uri,tipo', [
    ('mongodb://127.0.0.1:27028/', 'MongoDB local'),
    ('mongodb+srv://usuario:clave@cluster.mongodb.net/?retryWrites=true&w=majority', 'MongoDB Atlas'),
    ('mongodb+srv://usuario:clave@cluster.mongodb.net/gamefinder_pruebas?authSource=admin', 'MongoDB Atlas'),
])
def test_admite_solo_destinos_de_prueba_explicitos(uri, tipo):
    assert validar_configuracion(uri, 'gamefinder_pruebas') == tipo


@pytest.mark.asyncio
async def test_no_reclama_ni_limpia_una_base_con_datos_anteriores():
    db = AsyncMongoMockClient()['gamefinder_pruebas']
    await db.juegos.insert_one({'titulo': 'Documento ajeno'})
    with pytest.raises(ValueError):
        await reclamar(db)
    with pytest.raises(RuntimeError):
        await limpiar_colecciones(db, 'no-autorizado')
    assert await db.juegos.count_documents({}) == 1


@pytest.mark.asyncio
async def test_limpieza_exige_propiedad_y_respeta_otras_bases():
    mongo = AsyncMongoMockClient()
    db = mongo['gamefinder_pruebas']
    await mongo['GameFinder'].juegos.insert_one({'titulo': 'Documento ajeno'})
    token = await reclamar(db)
    await db.juegos.insert_one({'titulo': 'Documento temporal sintético'})
    with pytest.raises(RuntimeError):
        await limpiar_colecciones(db, 'otra-ejecucion')
    assert await db.juegos.count_documents({}) == 1
    await limpiar_colecciones(db, token)
    assert await db.juegos.count_documents({}) == 0
    assert await db[MARCADOR].count_documents({}) == 1
    assert await mongo['GameFinder'].juegos.count_documents({}) == 1
    await liberar(db, token)
    assert set(await db.list_collection_names()).isdisjoint({*COLECCIONES, MARCADOR})


@pytest.mark.asyncio
async def test_no_limpia_si_aparecen_colecciones_ajenas_o_se_perdio_el_marcador():
    db = AsyncMongoMockClient()['gamefinder_pruebas']
    token = await reclamar(db)
    await db.juegos.insert_one({'titulo': 'Temporal sintético'})
    await db.ajena.insert_one({'origen': 'otra-aplicacion'})
    with pytest.raises(RuntimeError):
        await liberar(db, token)
    assert await db.juegos.count_documents({}) == 1 and await db.ajena.count_documents({}) == 1
    await db.drop_collection('ajena')
    await db.drop_collection(MARCADOR)
    with pytest.raises(RuntimeError):
        await limpiar_colecciones(db, token)
    assert await db.juegos.count_documents({}) == 1


@pytest.mark.asyncio
async def test_no_reclama_una_base_del_producto_aunque_este_vacia():
    db = AsyncMongoMockClient()['GameFinder']
    with pytest.raises(ValueError):
        await reclamar(db)
    assert await db.list_collection_names() == []
