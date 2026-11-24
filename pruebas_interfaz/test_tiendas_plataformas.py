"""Relación tienda/plataforma con MongoDB emulado, sin acceder al Atlas real."""
import pytest
from bson import ObjectId
from pruebas_interfaz.conftest import register, login


async def preparar(env):
    c, db, _, gid, tid = env
    user = await register(c); await login(c)
    await db.usuarios.update_one({'_id': ObjectId(user['_id'])}, {'$set': {'rol': 'admin'}})
    await db.juegos.update_one({'_id': ObjectId(gid)}, {'$set': {'plataformas': ['PC', 'PS5', 'Xbox']}})
    return c, db, gid, tid


async def configurar(c, tid, plataformas):
    return await c.put('/tiendas/' + tid, json={'nombre': 'Tienda sintética', 'plataformas': plataformas})


async def oferta(c, gid, tid, plataforma='PC', legacy=False):
    return await c.post(f'/juegos/{gid}/' + ('tiendas' if legacy else 'ofertas'), json={
        'tiendaId': tid, 'precio': 10000, **({'plataforma': plataforma} if plataforma is not None else {})})


@pytest.mark.asyncio
async def test_tienda_admite_varias_plataformas_y_listado_no_supone_soporte(env):
    c, db, gid, tid = await preparar(env)
    created = await c.post('/tiendas/', json={'nombre': 'Tienda multiplaforma de prueba', 'plataformas': [' PC ', 'PS5', 'pc']})
    assert created.status_code == 201, created.text
    store = created.json()
    assert store['plataformas'] == ['PC', 'PS5']
    assert (await c.get('/tiendas/' + store['_id'])).json()['plataformas'] == ['PC', 'PS5']
    found = (await c.get('/tiendas/?plataforma=PC')).json()
    assert [s['_id'] for s in found] == [store['_id']]
    assert (await c.get('/tiendas/?plataforma=Xbox')).json() == []
    assert len((await c.get('/tiendas/')).json()) == 2
    assert 'plataformas' not in (await c.get('/tiendas/' + tid)).json()


@pytest.mark.asyncio
async def test_oferta_debe_ser_compatible_con_tienda_y_juego(env):
    c, db, gid, tid = await preparar(env)
    assert (await configurar(c, tid, ['PC'])).status_code == 200
    before = await db.juegos.find_one({'_id': ObjectId(gid)})
    assert (await oferta(c, gid, tid, 'PS5')).status_code == 422
    assert (await oferta(c, gid, tid, 'Nintendo Switch')).status_code == 422
    assert await db.juegos.find_one({'_id': ObjectId(gid)}) == before
    assert (await oferta(c, gid, tid)).status_code == 201
    assert (await c.get(f'/juegos/{gid}/ofertas?plataforma=PS5')).json()['ofertas'] == []


@pytest.mark.asyncio
async def test_edicion_por_id_y_ruta_antigua_no_eluden_restricciones(env):
    c, db, gid, tid = await preparar(env)
    await configurar(c, tid, ['PC'])
    created = (await oferta(c, gid, tid)).json()['precios'][0]
    before = await db.juegos.find_one({'_id': ObjectId(gid)})
    for path in [f"/juegos/{gid}/ofertas/{created['ofertaId']}", f'/juegos/{gid}/tiendas/{tid}?plataforma=PC&moneda=CLP']:
        assert (await c.put(path, json={'plataforma': 'PS5'})).status_code == 422
        assert (await c.put(path, json={'plataforma': None})).status_code == 422
    assert await db.juegos.find_one({'_id': ObjectId(gid)}) == before
    assert (await c.put(f"/juegos/{gid}/ofertas/{created['ofertaId']}", json={'precio': 9000})).status_code == 200


@pytest.mark.asyncio
async def test_no_restringir_tienda_si_hay_ofertas_incompatibles(env):
    c, db, gid, tid = await preparar(env)
    await configurar(c, tid, ['PC', 'PS5'])
    await oferta(c, gid, tid, 'PS5')
    before = await db.tiendas.find_one({'_id': ObjectId(tid)})
    rejected = await configurar(c, tid, ['PC'])
    assert rejected.status_code == 409, rejected.text
    assert await db.tiendas.find_one({'_id': ObjectId(tid)}) == before
    assert (await configurar(c, tid, ['PC', 'PS5', 'Xbox'])).status_code == 200


@pytest.mark.asyncio
async def test_guardia_de_tienda_incluye_ids_antiguos_en_texto_y_juegos_ocultos(env):
    c, db, gid, tid = await preparar(env)
    await db.juegos.update_one({'_id': ObjectId(gid)}, {'$set': {
        'activo': False, 'precios': [{'tiendaId': tid, 'plataforma': 'PS5', 'precio': 1, 'moneda': 'CLP'}]}})
    assert (await configurar(c, tid, ['PC'])).status_code == 409
    assert (await configurar(c, tid, ['PS5'])).status_code == 200


@pytest.mark.asyncio
async def test_configurar_tienda_no_asigna_plataformas_a_precios_antiguos(env):
    c, db, gid, tid = await preparar(env)
    original_game = env[2]
    before = await db.juegos.find_one({'_id': ObjectId(original_game)})
    assert (await configurar(c, tid, ['PC'])).status_code == 200
    await c.get(f'/juegos/{original_game}/ofertas')
    assert await db.juegos.find_one({'_id': ObjectId(original_game)}) == before
    # No se permite añadir precios generales nuevos a una tienda ya configurada.
    assert (await oferta(c, gid, tid, None, legacy=True)).status_code == 422
    changed = await c.put(f'/juegos/{original_game}/tiendas/{tid}?sin_plataforma=true&moneda=CLP', json={'plataforma': 'PC'})
    assert changed.status_code == 200, changed.text
    assert changed.json()['precios'][0]['precio'] == before['precios'][0]['precio']


@pytest.mark.asyncio
async def test_compatibilidad_de_tienda_sin_configurar_y_edicion_anterior(env):
    c, db, gid, tid = await preparar(env)
    assert (await oferta(c, gid, tid, 'PS5')).status_code == 201
    assert (await oferta(c, gid, tid, None, legacy=True)).status_code == 201
    assert (await configurar(c, tid, ['PC', 'PS5'])).status_code == 200
    assert (await c.put('/tiendas/' + tid, json={'nombre': 'Solo cambia el nombre'})).status_code == 200
    assert (await c.get('/tiendas/' + tid)).json()['plataformas'] == ['PC', 'PS5']
    assert (await configurar(c, tid, None)).status_code == 200
    assert (await c.get('/tiendas/' + tid)).json()['plataformas'] is None


@pytest.mark.asyncio
async def test_heredados_incompatibles_se_pueden_corregir_o_eliminar(env):
    c, db, gid, tid = await preparar(env)
    await configurar(c, tid, ['PC'])
    oid = str(ObjectId())
    await db.juegos.update_one({'_id': ObjectId(gid)}, {'$set': {'precios': [
        {'ofertaId': oid, 'tiendaId': ObjectId(tid), 'plataforma': 'PS5', 'precio': 1, 'moneda': 'CLP'}]}})
    assert (await c.put(f'/juegos/{gid}/ofertas/{oid}', json={'precio': 2})).status_code == 422
    assert (await c.put(f'/juegos/{gid}/ofertas/{oid}', json={'plataforma': 'PC'})).status_code == 200
    assert (await c.delete(f'/juegos/{gid}/ofertas/{oid}')).status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize('plataformas', [[], [''], [' '], ['x' * 101], 'PC', [None], ['PC'] * 51])
async def test_plataformas_invalidas_no_se_guardan(env, plataformas):
    c, db, gid, tid = await preparar(env)
    before = await db.tiendas.find_one({'_id': ObjectId(tid)})
    assert (await configurar(c, tid, plataformas)).status_code == 422
    assert await db.tiendas.find_one({'_id': ObjectId(tid)}) == before


@pytest.mark.asyncio
async def test_configurar_plataformas_requiere_admin(env):
    c, db, _, gid, tid = env
    assert (await configurar(c, tid, ['PC'])).status_code == 401
    await register(c); await login(c)
    assert (await configurar(c, tid, ['PC'])).status_code == 403
    assert (await c.post('/tiendas/', json={'nombre': 'No autorizada', 'plataformas': ['PC']})).status_code == 403


@pytest.mark.asyncio
async def test_restringir_tienda_no_confunde_ofertas_de_otras_tiendas(env):
    c, db, gid, tid = await preparar(env)
    other = ObjectId()
    await db.tiendas.insert_one({'_id': other, 'nombre': 'Otra tienda sintética'})
    await oferta(c, gid, tid, 'PC')
    await oferta(c, gid, str(other), 'PS5')
    assert (await configurar(c, tid, ['PC'])).status_code == 200
