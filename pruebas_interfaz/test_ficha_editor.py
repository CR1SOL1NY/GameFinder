"""Escrituras administrativas sobre mongomock, nunca sobre el Atlas del usuario."""
import pytest
from bson import ObjectId
from pruebas_interfaz.conftest import register, login


async def admin(client, db):
    user = await register(client)
    await login(client)
    await db.usuarios.update_one({'_id': ObjectId(user['_id'])}, {'$set': {'rol': 'admin'}})


def ficha():
    return {'titulo': 'Ficha sintética', 'plataformas': ['PC', 'PS5'],
            'descripcionCorta': 'Resumen verificado de prueba',
            'caracteristicas': [' Exploración de prueba ', 'exploración DE prueba', 'Cooperativo de prueba'],
            'requisitosSistema': {'plataforma': 'PC',
                'minimos': {'procesador': 'CPU de prueba', 'memoria': '  '},
                'recomendados': {'memoria': 'Memoria de prueba'}}}


@pytest.mark.asyncio
async def test_crear_y_consultar_ficha_completa(env):
    c, db, *_ = env
    await admin(c, db)
    created = await c.post('/juegos/', json=ficha())
    assert created.status_code == 201, created.text
    game = created.json()
    assert game['caracteristicas'] == ['Exploración de prueba', 'Cooperativo de prueba']
    assert game['requisitosSistema']['minimos']['memoria'] is None
    assert game['requisitosSistema']['recomendados']['memoria'] == 'Memoria de prueba'
    assert game['precios'] == [] and game['imagenPortada'] is None
    public = (await c.get('/juegos/' + game['_id'])).json()
    assert public['descripcionCorta'] == game['descripcionCorta']
    assert public['requisitosSistema'] == game['requisitosSistema']


@pytest.mark.asyncio
async def test_cliente_anterior_y_edicion_simple_conservan_datos(env):
    c, db, gid, *_ = env
    await admin(c, db)
    original = await db.juegos.find_one({'_id': ObjectId(gid)})
    await db.juegos.update_one({'_id': ObjectId(gid)}, {'$set': {
        'descripcionCorta': 'Resumen anterior', 'caracteristicas': ['Dato anterior'],
        'imagenFondo': 'https://example.com/existente.jpg', 'metadatosCatalogo': {'fuente': 'Anterior'},
        'requisitosSistema': {'minimos': {'notas': 'Heredado sin plataforma', 'campoAnterior': 'Se conserva'}}}})
    before = await db.juegos.find_one({'_id': ObjectId(gid)})
    updated = await c.put('/juegos/' + gid, json={'titulo': 'Solo cambia el título'})
    assert updated.status_code == 200, updated.text
    after = await db.juegos.find_one({'_id': ObjectId(gid)})
    assert after == {**before, 'titulo': 'Solo cambia el título'}
    assert after['precios'] == original['precios']


@pytest.mark.asyncio
async def test_borrar_campos_opcionales_es_explicito(env):
    c, db, *_ = env
    await admin(c, db)
    game = (await c.post('/juegos/', json=ficha())).json()
    changed = await c.put('/juegos/' + game['_id'], json={
        'titulo': game['titulo'], 'descripcionCorta': None, 'caracteristicas': [], 'requisitosSistema': None})
    assert changed.status_code == 200, changed.text
    assert changed.json()['descripcionCorta'] is None
    assert changed.json()['caracteristicas'] == []
    assert changed.json()['requisitosSistema'] is None
    assert changed.json()['plataformas'] == ['PC', 'PS5']


@pytest.mark.asyncio
async def test_no_retirar_plataforma_de_requisitos_sin_corregir_bloque(env):
    c, db, *_ = env
    await admin(c, db)
    game = (await c.post('/juegos/', json=ficha())).json()
    path = '/juegos/' + game['_id']
    rejected = await c.put(path, json={'titulo': game['titulo'], 'plataformas': ['PS5']})
    assert rejected.status_code == 422
    unchanged = (await c.get(path)).json()
    assert unchanged['plataformas'] == ['PC', 'PS5']
    accepted = await c.put(path, json={'titulo': game['titulo'], 'plataformas': ['PS5'], 'requisitosSistema': None})
    assert accepted.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize('extra', [
    {'descripcionCorta': 'x' * 601}, {'caracteristicas': [' ']}, {'caracteristicas': ['x' * 301]},
    {'caracteristicas': [f'Dato {n}' for n in range(31)]},
    {'requisitosSistema': {'plataforma': 'PC', 'minimos': {}}},
    {'requisitosSistema': {'plataforma': 'PC'}},
    {'requisitosSistema': {'minimos': {'procesador': 'Prueba'}}},
    {'requisitosSistema': {'plataforma': 'Xbox', 'minimos': {'procesador': 'Prueba'}}},
    {'requisitosSistema': {'plataforma': 'PC', 'minimos': {'campoInventado': 'Prueba'}}},
    {'requisitosSistema': {'plataforma': 'PC', 'minimos': {'procesador': ['Prueba']}}},
    {'requisitosSistema': {'plataforma': 'PC', 'minimos': {'notas': 'x' * 2001}}},
])
async def test_datos_invalidos_no_se_guardan(env, extra):
    c, db, gid, *_ = env
    await admin(c, db)
    before = await db.juegos.find_one({'_id': ObjectId(gid)})
    response = await c.put('/juegos/' + gid, json={'titulo': 'No debe cambiar', **extra})
    assert response.status_code == 422, response.text
    assert await db.juegos.find_one({'_id': ObjectId(gid)}) == before


@pytest.mark.asyncio
async def test_ficha_solo_admin_y_sin_inyectar_ofertas(env):
    c, db, gid, *_ = env
    assert (await c.put('/juegos/' + gid, json={'titulo': 'No autorizado'})).status_code == 401
    await register(c); await login(c)
    assert (await c.post('/juegos/', json=ficha())).status_code == 403
    assert (await c.put('/juegos/' + gid, json=ficha())).status_code == 403
    user = await db.usuarios.find_one({'correo': 'ana@example.com'})
    await db.usuarios.update_one({'_id': user['_id']}, {'$set': {'rol': 'admin'}})
    before = await db.juegos.find_one({'_id': ObjectId(gid)})
    result = await c.put('/juegos/' + gid, json={'titulo': before['titulo'], 'precios': [], 'precio_mas_barato': None})
    assert result.status_code == 200
    assert result.json()['precios'] == (await c.get('/juegos/' + gid)).json()['precios']
    assert (await db.juegos.find_one({'_id': ObjectId(gid)}))['precios'] == before['precios']


@pytest.mark.asyncio
async def test_cambio_concurrente_de_plataforma_no_deja_requisitos_incompatibles(env):
    from integracion_frontend.database import get_db
    from integracion_frontend.aplicacion import app
    c, db, gid, *_ = env
    await admin(c, db)
    before = await db.juegos.find_one({'_id': ObjectId(gid)})

    class ColeccionConCarrera:
        async def find_one(self, query):
            return await db.juegos.find_one(query)

        async def update_one(self, query, update):
            # Un segundo administrador cambia la plataforma después de la lectura.
            await db.juegos.update_one({'_id': ObjectId(gid)}, {'$set': {'plataformas': ['PS5'], 'requisitosSistema': None}})
            return await db.juegos.update_one(query, update)

    class BaseConCarrera:
        juegos = ColeccionConCarrera()

        def __getattr__(self, name):
            return getattr(db, name)

    app.dependency_overrides[get_db] = lambda: BaseConCarrera()
    response = await c.put('/juegos/' + gid, json={
        'titulo': 'No debe sobrescribir',
        'requisitosSistema': {'plataforma': 'PC', 'minimos': {'notas': 'Dato sintético'}}})
    assert response.status_code == 409, response.text
    after = await db.juegos.find_one({'_id': ObjectId(gid)})
    assert after['titulo'] == before['titulo']
    assert after['plataformas'] == ['PS5'] and after['requisitosSistema'] is None
