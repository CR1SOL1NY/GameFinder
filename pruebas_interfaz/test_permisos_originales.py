"""Autorización de la API original, con documentos sintéticos en una BD aislada."""
from datetime import datetime, timedelta, timezone

import bcrypt
import httpx
import jwt
import pytest
import pytest_asyncio
from bson import ObjectId

from app.database import get_db
from app.limiter import limiter
from integracion_frontend import config
from main import app as original
from main_interfaz import app


@pytest_asyncio.fixture
async def original_env(env):
    _, db, gid, gid2, tid = env
    previous = limiter.enabled
    limiter.enabled = False
    app.dependency_overrides[get_db] = lambda: db
    password = 'ClaveSintetica123!'
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()
    users = {}
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://testserver',
                                     headers={'Origin': 'http://localhost:5173'}) as client:
            for name, role in [('ana', 'usuario'), ('bea', 'usuario'), ('admin', 'admin')]:
                uid = ObjectId()
                await db.usuarios.insert_one({
                    '_id': uid, 'nombre': name, 'correo': f'{name}@example.com',
                    'contrasenaHash': hashed, 'rol': role, 'activo': True, 'listaDeseados': [],
                    'preferencias': {'generos': ['RPG'], 'precioMin': 0, 'precioMax': 50000},
                    'datoInternoNoPublico': 'solo-servidor',
                })
                login = await client.post('/usuarios/login', json={'correo': f'{name}@example.com', 'contrasena': password})
                assert login.status_code == 200, login.text
                data = login.json()
                assert data['token_type'] == 'bearer' and data['usuario']['id'] == str(uid)
                users[name] = {'id': str(uid), 'token': data['access_token']}
            yield client, db, gid, gid2, tid, users
    finally:
        app.dependency_overrides.clear()
        limiter.enabled = previous


def auth(user):
    return {'Authorization': 'Bearer ' + user['token']}


async def snapshot(db):
    return {name: await db[name].find().sort('_id', 1).to_list(length=1000)
            for name in ('usuarios', 'juegos', 'tiendas', 'calificaciones', 'sesiones')}


def test_la_entrada_original_utiliza_la_misma_politica():
    assert app is original
    from app.security import get_current_user as legacy_guard
    from integracion_frontend.security import get_current_user as frontend_guard
    assert legacy_guard is frontend_guard


@pytest.mark.asyncio
@pytest.mark.parametrize('role,expected', [(None, 401), ('ana', 403)])
@pytest.mark.parametrize('operation', ['add_offer', 'update_offer', 'delete_offer', 'delete_game', 'delete_store', 'list_users'])
async def test_operaciones_administrativas_rechazan_acceso_y_no_escriben(original_env, role, expected, operation):
    client, db, gid, _, tid, users = original_env
    routes = {
        'add_offer': ('POST', f'/juegos/{gid}/tiendas', {'tiendaId': tid, 'precio': 900, 'urlProducto': 'https://example.com/juego'}),
        'update_offer': ('PUT', f'/juegos/{gid}/tiendas/{tid}', {'precio': 900}),
        'delete_offer': ('DELETE', f'/juegos/{gid}/tiendas/{tid}', None),
        'delete_game': ('DELETE', f'/juegos/{gid}', None),
        'delete_store': ('DELETE', f'/tiendas/{tid}', None),
        'list_users': ('GET', '/usuarios/', None),
    }
    method, path, body = routes[operation]
    before = await snapshot(db)
    result = await client.request(method, path, json=body, headers=auth(users[role]) if role else {})
    assert result.status_code == expected, result.text
    assert await snapshot(db) == before


@pytest.mark.asyncio
@pytest.mark.parametrize('role,expected', [(None, 401), ('bea', 403), ('admin', 403)])
@pytest.mark.parametrize('operation', ['wishlist', 'recommendations', 'add_wish', 'remove_wish', 'delete_user'])
async def test_datos_y_cuenta_solo_del_titular(original_env, role, expected, operation):
    client, db, gid, _, _, users = original_env
    uid = users['ana']['id']
    paths = {
        'wishlist': ('GET', f'/usuarios/{uid}/deseados'),
        'recommendations': ('GET', f'/usuarios/{uid}/recomendaciones'),
        'add_wish': ('PUT', f'/usuarios/{uid}/deseados/{gid}'),
        'remove_wish': ('DELETE', f'/usuarios/{uid}/deseados/{gid}'),
        'delete_user': ('DELETE', f'/usuarios/{uid}'),
    }
    before = await snapshot(db)
    method, path = paths[operation]
    response = await client.request(method, path, headers=auth(users[role]) if role else {})
    assert response.status_code == expected, response.text
    assert await snapshot(db) == before


@pytest.mark.asyncio
async def test_perfiles_privados_y_respuestas_sin_campos_internos(original_env):
    client, _, _, _, _, users = original_env
    path = '/usuarios/' + users['ana']['id']
    anonymous = await client.get(path)
    assert anonymous.status_code == 401 and anonymous.headers['cache-control'] == 'no-store'
    assert (await client.get(path, headers=auth(users['bea']))).status_code == 403
    for role in ('ana', 'admin'):
        response = await client.get(path, headers=auth(users[role]))
        assert response.status_code == 200 and response.json()['_id'] == users['ana']['id']
        assert 'contrasenaHash' not in response.json() and 'datoInternoNoPublico' not in response.json()
        assert '_sessionId' not in response.json()
    listing = await client.get('/usuarios/', headers=auth(users['admin']))
    assert listing.status_code == 200 and len(listing.json()) == 3
    assert listing.headers['cache-control'] == 'no-store'
    assert all('contrasenaHash' not in u and 'datoInternoNoPublico' not in u for u in listing.json())


@pytest.mark.asyncio
async def test_deseados_y_recomendaciones_propias_conservan_el_contrato(original_env):
    client, db, gid, _, _, users = original_env
    owner = users['ana']
    path = f"/usuarios/{owner['id']}/deseados"
    assert (await client.put(f'{path}/{gid}', headers=auth(owner))).status_code == 200
    assert (await client.put(f'{path}/{gid}', headers=auth(owner))).status_code == 409
    result = await client.get(path, headers=auth(owner))
    assert result.status_code == 200 and result.json()['totalDeseados'] == 1
    assert result.json()['listaDeseados'][0]['juegoId'] == gid
    assert (await client.get(f"/usuarios/{owner['id']}/recomendaciones", headers=auth(owner))).status_code == 200
    assert (await client.delete(f'{path}/{gid}', headers=auth(owner))).status_code == 200
    assert (await db.usuarios.find_one({'_id': ObjectId(owner['id'])}))['listaDeseados'] == []


@pytest.mark.asyncio
async def test_eliminar_cuenta_propia_revoca_sus_sesiones(original_env):
    client, db, _, _, _, users = original_env
    owner = users['ana']
    response = await client.delete(f"/usuarios/{owner['id']}", headers=auth(owner))
    assert response.status_code == 200
    assert await db.usuarios.find_one({'_id': ObjectId(owner['id'])}) is None
    assert await db.sesiones.count_documents({'usuarioId': ObjectId(owner['id'])}) == 0
    assert await db.usuarios.count_documents({}) == 2
    assert (await client.get('/interfaz/usuarios/me', headers=auth(owner))).status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize('route', ['global', 'game'])
async def test_publicar_resena_exige_sesion_y_autor_correcto(original_env, route):
    client, db, gid, _, _, users = original_env
    body = {'usuarioId': users['bea']['id'], 'juegoId': gid, 'puntaje': 4, 'comentario': 'Reseña sintética', 'visible': False}
    path = '/calificaciones/' if route == 'global' else f'/juegos/{gid}/calificaciones'
    before = await snapshot(db)
    assert (await client.post(path, json=body)).status_code == 401
    assert (await client.post(path, json=body, headers=auth(users['ana']))).status_code == 403
    assert await snapshot(db) == before
    body['usuarioId'] = users['ana']['id']
    created = await client.post(path, json=body, headers=auth(users['ana']))
    assert created.status_code == 201, created.text
    assert created.json()['usuarioId'] == users['ana']['id'] and created.json()['visible'] is True
    other_path = f'/juegos/{gid}/calificaciones' if route == 'global' else '/calificaciones/'
    assert (await client.post(other_path, json=body, headers=auth(users['ana']))).status_code == 409
    assert await db.calificaciones.count_documents({}) == 1


async def insert_review(db, gid, user, visible=True, score=4):
    result = await db.calificaciones.insert_one({'usuarioId': ObjectId(user['id']), 'juegoId': ObjectId(gid),
        'puntaje': score, 'comentario': 'Reseña sintética', 'fecha': datetime.now(timezone.utc), 'visible': visible})
    return str(result.inserted_id)


@pytest.mark.asyncio
@pytest.mark.parametrize('method', ['PUT', 'DELETE'])
async def test_reseñas_ajenas_no_se_pueden_modificar(original_env, method):
    client, db, gid, _, _, users = original_env
    rid = await insert_review(db, gid, users['ana'])
    path = '/calificaciones/' + rid
    before = await snapshot(db)
    for role in (None, 'bea'):
        result = await client.request(method, path, headers=auth(users[role]) if role else {},
                                      json={'puntaje': 1} if method == 'PUT' else None)
        assert result.status_code == (401 if role is None else 403)
    if method == 'PUT':
        assert (await client.put(path, json={'puntaje': 1}, headers=auth(users['admin']))).status_code == 403
    assert await snapshot(db) == before
    result = await client.request(method, path, headers=auth(users['ana']),
                                  json={'puntaje': 5, 'comentario': 'Actualizada'} if method == 'PUT' else None)
    assert result.status_code == 200, result.text
    row = await db.calificaciones.find_one({'_id': ObjectId(rid)})
    if method == 'PUT':
        assert row['puntaje'] == 5 and row['comentario'] == 'Actualizada'
    else:
        assert row is None


@pytest.mark.asyncio
async def test_administrador_puede_moderar_sin_reescribir_opiniones(original_env):
    client, db, gid, gid2, tid, users = original_env
    rid = await insert_review(db, gid, users['ana'])
    assert (await client.delete('/calificaciones/' + rid, headers=auth(users['admin']))).status_code == 200
    # Se ejecutan eliminaciones reales únicamente sobre documentos sintéticos.
    unused = ObjectId()
    await db.tiendas.insert_one({'_id': unused, 'nombre': 'Tienda descartable de prueba'})
    assert (await client.delete('/tiendas/' + str(unused), headers=auth(users['admin']))).status_code == 200
    assert await db.tiendas.find_one({'_id': unused}) is None
    assert (await client.delete('/tiendas/' + tid, headers=auth(users['admin']))).status_code == 409
    assert (await client.delete('/juegos/' + gid2, headers=auth(users['admin']))).status_code == 200
    assert await db.juegos.find_one({'_id': ObjectId(gid2)}) is None


@pytest.mark.asyncio
@pytest.mark.parametrize('method', ['POST', 'PUT', 'DELETE'])
async def test_administrador_llega_al_control_de_ofertas_inexistentes(original_env, method):
    client, db, gid, _, _, users = original_env
    missing = str(ObjectId())
    path = f'/juegos/{gid}/tiendas' if method == 'POST' else f'/juegos/{gid}/tiendas/{missing}'
    body = {'tiendaId': missing, 'precio': 100, 'urlProducto': 'https://example.com'} if method == 'POST' else {'precio': 100}
    before = await snapshot(db)
    result = await client.request(method, path, json=body, headers=auth(users['admin']))
    assert result.status_code == 404, result.text
    assert await snapshot(db) == before
    # No se simula que mongomock ejecute $sortArray: ese pipeline requiere MongoDB real.


@pytest.mark.asyncio
async def test_no_se_publican_reseñas_ocultas_ni_juegos_deshabilitados(original_env):
    client, db, gid, gid2, _, users = original_env
    rid = await insert_review(db, gid, users['ana'], score=5)
    await insert_review(db, gid, users['bea'], visible=False, score=1)
    await db.juegos.update_one({'_id': ObjectId(gid2)}, {'$set': {'activo': False}})
    for path in (f'/juegos/{gid}/calificaciones', f'/calificaciones/juego/{gid}'):
        reviews = await client.get(path)
        assert reviews.status_code == 200 and [r['_id'] for r in reviews.json()] == [rid]
    catalog = await client.get('/juegos/')
    assert catalog.status_code == 200, catalog.text
    assert len(catalog.json()) == 1 and catalog.json()[0]['totalCalificaciones'] == 1
    assert catalog.json()[0]['promedioCalificaciones'] == 5
    stats = await client.get('/juegos/estadisticas/calificaciones')
    assert stats.status_code == 200 and stats.json()[0]['promedio_puntaje'] == 5
    assert stats.json()[0]['total_reseñas'] == 1
    assert (await client.get('/juegos/buscar', params={'q': 'Beta'})).status_code == 404
    for path in (f'/juegos/{gid2}', f'/juegos/{gid2}/tiendas', f'/juegos/{gid2}/calificaciones', f'/calificaciones/juego/{gid2}'):
        assert (await client.get(path)).status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize('logout', ['/usuarios/logout', '/interfaz/usuarios/logout'])
async def test_logout_revoca_el_token_en_ambas_apis(original_env, logout):
    client, db, _, _, _, users = original_env
    owner = users['ana']
    assert (await client.get('/usuarios/' + owner['id'], headers=auth(owner))).status_code == 200
    assert (await client.get('/interfaz/usuarios/me', headers=auth(owner))).status_code == 200
    result = await client.post(logout, headers=auth(owner))
    assert result.status_code == 200, result.text
    assert (await client.get('/usuarios/' + owner['id'], headers=auth(owner))).status_code == 401
    assert (await client.get('/interfaz/usuarios/me', headers=auth(owner))).status_code == 401
    assert await db.sesiones.count_documents({'usuarioId': ObjectId(owner['id'])}) == 0


@pytest.mark.asyncio
async def test_sesion_cookie_del_front_no_elude_origen_en_rutas_originales(original_env):
    client, _, _, _, _, users = original_env
    login = await client.post('/interfaz/usuarios/login', json={'correo': 'ana@example.com', 'contrasena': 'ClaveSintetica123!'})
    assert login.status_code == 200 and 'HttpOnly' in login.headers['set-cookie']
    result = await client.post('/usuarios/logout', headers={'Origin': 'https://otro.example.com'})
    assert result.status_code == 403
    assert (await client.get('/usuarios/' + users['ana']['id'])).status_code == 200
    assert (await client.post('/usuarios/logout')).status_code == 200
    assert (await client.get('/interfaz/usuarios/me')).status_code == 401


@pytest.mark.asyncio
async def test_cuentas_inactivas_roles_en_db_y_tokens_invalidos(original_env):
    client, db, _, _, tid, users = original_env
    user = users['ana']
    payload = jwt.decode(user['token'], config.JWT_SECRET_KEY, algorithms=['HS256'])
    for data in (
        {k: v for k, v in payload.items() if k != 'jti'},
        {**payload, 'exp': datetime.now(timezone.utc) - timedelta(seconds=1)},
        {**payload, 'jti': 'sesion-que-no-existe'},
        {**payload, 'sub': {'$ne': None}},
    ):
        token = jwt.encode(data, config.JWT_SECRET_KEY, algorithm='HS256')
        assert (await client.get('/usuarios/' + user['id'], headers={'Authorization': 'Bearer ' + token})).status_code == 401
    assert (await client.get('/usuarios/' + user['id'], headers={'Authorization': 'Bearer alterado'})).status_code == 401
    # Un rol declarado en el JWT no sustituye el rol guardado en la base.
    fake_role = jwt.encode({**payload, 'rol': 'admin'}, config.JWT_SECRET_KEY, algorithm='HS256')
    assert (await client.delete('/tiendas/' + tid, headers={'Authorization': 'Bearer ' + fake_role})).status_code == 403
    await db.usuarios.update_one({'_id': ObjectId(user['id'])}, {'$set': {'activo': False}})
    assert (await client.get('/usuarios/' + user['id'], headers=auth(user))).status_code == 401
    assert (await client.post('/usuarios/login', json={'correo': 'ana@example.com', 'contrasena': 'ClaveSintetica123!'})).status_code == 401
    await db.usuarios.update_one({'_id': ObjectId(users['admin']['id'])}, {'$set': {'rol': 'usuario'}})
    assert (await client.get('/usuarios/', headers=auth(users['admin']))).status_code == 403


@pytest.mark.asyncio
async def test_registro_original_no_permite_elegir_rol_admin(original_env):
    client, db, *_ = original_env
    hashed = bcrypt.hashpw(b'ClaveRegistro123!', bcrypt.gensalt(rounds=4)).decode()
    result = await client.post('/usuarios/', json={'nombre': 'Registro de prueba', 'correo': 'nuevo@example.com',
        'contrasenaHash': hashed, 'rol': 'admin', 'activo': False})
    assert result.status_code == 201 and result.json()['rol'] == 'usuario', result.text
    stored = await db.usuarios.find_one({'correo': 'nuevo@example.com'})
    assert stored['rol'] == 'usuario' and stored['activo'] is True
    assert 'contrasenaHash' not in result.json()
