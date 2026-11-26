"""Medias estrellas y lectura de precios propios. Fixtures emulados; nunca Atlas."""
import pytest
from bson import ObjectId
from pydantic import ValidationError
from integracion_frontend.schemas import CalificacionCreate, CalificacionJuegoCreate, CalificacionUpdate
from pruebas_interfaz.conftest import register, login


@pytest.mark.parametrize('value', [0, -0.5, 5.5, 2.25, 4.2, True, False, '3.5', float('inf'), float('nan')])
def test_rating_contracts_reject_invalid_steps_and_types(value):
    for model, extra in [(CalificacionCreate, {'juegoId': str(ObjectId())}), (CalificacionJuegoCreate, {}), (CalificacionUpdate, {})]:
        with pytest.raises(ValidationError):
            model(puntaje=value, **extra)


@pytest.mark.asyncio
async def test_half_stars_persist_in_both_routes_updates_and_real_averages(env):
    c, db, gid, gid2, _ = env
    u = await register(c)
    await login(c)
    first = await c.post('/calificaciones/', json={'juegoId': gid, 'puntaje': 0.5, 'comentario': 'Media estrella de prueba'})
    assert first.status_code == 201, first.text
    rid = first.json()['_id']
    assert (await c.get('/calificaciones/mia/' + gid)).json()['puntaje'] == 0.5
    assert (await c.put('/calificaciones/' + rid, json={'puntaje': 3.5})).status_code == 200
    assert (await c.post(f'/juegos/{gid2}/calificaciones', json={'puntaje': 4.5})).status_code == 201
    assert (await c.get('/juegos/' + gid)).json()['promedioCalificaciones'] == 3.5
    summary = (await c.get('/usuarios/me/resumen-calificaciones')).json()
    assert summary['total'] == 2 and summary['promedio'] == 4
    assert sorted(r['puntaje'] for r in summary['ultimas']) == [3.5, 4.5]
    assert (await c.put('/calificaciones/' + rid, json={'puntaje': 3.25})).status_code == 422
    await register(c, 'otra@example.com')
    await login(c, 'otra@example.com')
    assert (await c.put('/calificaciones/' + rid, json={'puntaje': 2.5})).status_code == 403
    assert (await db.calificaciones.find_one({'_id': ObjectId(rid)}))['puntaje'] == 3.5


@pytest.mark.asyncio
async def test_wishlist_prices_are_authenticated_private_and_read_only(env):
    c, db, gid, gid2, tid = env
    path = '/usuarios/me/precios-deseados'
    assert (await c.get(path)).status_code == 401
    u = await register(c)
    await login(c)
    assert (await c.get(path)).json() == {'juegos': []}
    assert (await c.put(f"/usuarios/{u['_id']}/deseados/{gid}")).status_code == 200
    before = {name: await db[name].find().to_list(length=None) for name in await db.list_collection_names()}
    response = await c.get(path)
    assert response.status_code == 200, response.text
    games = response.json()['juegos']
    assert len(games) == 1 and games[0]['_id'] == gid
    assert {p['moneda'] for p in games[0]['precios']} == {'CLP', 'USD'}
    assert all(p['nombreTienda'] == 'Tienda de prueba (no real)' for p in games[0]['precios'])
    assert all(p.get('plataforma') is None for p in games[0]['precios'])
    after = {name: await db[name].find().to_list(length=None) for name in await db.list_collection_names()}
    assert before == after
    await register(c, 'otra@example.com')
    await login(c, 'otra@example.com')
    assert (await c.get(path, params={'usuarioId': u['_id']})).json() == {'juegos': []}


@pytest.mark.asyncio
async def test_prices_snapshot_preserves_variants_and_omits_inactive_games(env):
    c, db, gid, gid2, tid = env
    u = await register(c)
    await login(c)
    await c.put(f"/usuarios/{u['_id']}/deseados/{gid}")
    await c.put(f"/usuarios/{u['_id']}/deseados/{gid2}")
    await db.juegos.update_one({'_id': ObjectId(gid2)}, {'$set': {'activo': False}})
    await db.juegos.update_one({'_id': ObjectId(gid)}, {'$push': {'precios': {'tiendaId': ObjectId(tid), 'precio': 30000, 'plataforma': 'PS5', 'moneda': 'CLP'}}})
    games = (await c.get('/usuarios/me/precios-deseados')).json()['juegos']
    assert len(games) == 1 and games[0]['_id'] == gid
    assert len(games[0]['precios']) == 3
    assert games[0]['precios'][-1]['plataforma'] == 'PS5'
    assert games[0]['precios'][-1]['precio'] == 30000
