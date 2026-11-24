"""Regresiones con precios sintéticos: nunca se modifica Atlas."""
from datetime import datetime, timezone
import asyncio
import pytest
from bson import ObjectId
from pruebas_interfaz.conftest import register, login


async def admin(env):
    c, db, gid, gid2, tid = env
    u = await register(c)
    await login(c)
    await db.usuarios.update_one({'_id': ObjectId(u['_id'])}, {'$set': {'rol': 'admin'}})
    await db.juegos.update_one({'_id': ObjectId(gid2)}, {'$set': {'plataformas': ['PC', 'PS5', 'Xbox']}})
    return c, db, gid2, tid


async def add(c, gid, tid, platform='PC', currency='CLP', price=20000):
    r = await c.post(f'/juegos/{gid}/ofertas', json={'tiendaId': tid, 'plataforma': platform, 'moneda': currency, 'precio': price})
    assert r.status_code == 201, r.text
    return r.json()['precios'][-1]


@pytest.mark.asyncio
async def test_same_store_has_independent_platform_and_currency_prices(env):
    c, db, gid, tid = await admin(env)
    pc = await add(c, gid, tid)
    ps5 = await add(c, gid, tid, 'PS5', price=30000)
    usd = await add(c, gid, tid, currency='USD', price=15)
    assert len({pc['ofertaId'], ps5['ofertaId'], usd['ofertaId']}) == 3
    r = await c.put(f"/juegos/{gid}/ofertas/{ps5['ofertaId']}", json={'precio': 25000})
    assert r.status_code == 200, r.text
    assert [(p['plataforma'], p['moneda'], p['precio']) for p in r.json()['precios']] == [('PC', 'CLP', 20000), ('PS5', 'CLP', 25000), ('PC', 'USD', 15)]
    persisted = (await c.get(f'/juegos/{gid}')).json()['precios']
    assert [{k: v for k, v in p.items() if k != 'fechaActualizacion'} for p in persisted] == [{k: v for k, v in p.items() if k != 'fechaActualizacion'} for p in r.json()['precios']]
    assert (await c.delete(f"/juegos/{gid}/ofertas/{usd['ofertaId']}")).status_code == 200
    stored = await db.juegos.find_one({'_id': ObjectId(gid)})
    assert len(stored['precios']) == 2
    assert stored['precio_mas_barato']['precio'] == 20000
    assert stored['precio_mas_barato']['plataforma'] == 'PC'


@pytest.mark.asyncio
async def test_server_filters_and_summary_never_mix_platforms_or_currencies(env):
    c, db, gid, tid = await admin(env)
    await add(c, gid, tid, price=20000)
    await add(c, gid, tid, 'PS5', price=30000)
    await add(c, gid, tid, currency='USD', price=15)
    other = ObjectId()
    await db.tiendas.insert_one({'_id': other, 'nombre': 'Otra tienda de prueba'})
    await add(c, gid, str(other), price=18000)
    await c.post(f'/juegos/{gid}/tiendas', json={'tiendaId': tid, 'precio': 1, 'moneda': 'CLP'})
    result = (await c.get(f'/juegos/{gid}/ofertas', params={'plataforma': 'PC', 'moneda': 'CLP'})).json()
    assert result['totalOfertas'] == 2
    assert [p['precio'] for p in result['ofertas']] == [18000, 20000]
    assert all(p['plataforma'] == 'PC' and p['moneda'] == 'CLP' for p in result['ofertas'])
    assert result['resumen'] == [{'plataforma': 'PC', 'moneda': 'CLP', 'totalOfertas': 2, 'precioMinimo': 18000, 'tiendaId': str(other)}]
    assert result['ofertasSinPlataforma'] == 0
    all_offers = (await c.get(f'/juegos/{gid}/ofertas')).json()
    assert len(all_offers['resumen']) == 3 and all_offers['ofertasSinPlataforma'] == 1
    unknown = (await c.get(f'/juegos/{gid}/ofertas?sin_plataforma=true')).json()
    assert unknown['totalOfertas'] == 1 and unknown['ofertas'][0]['precio'] == 1 and unknown['resumen'] == []
    assert (await c.get(f'/juegos/{gid}/ofertas?plataforma=Xbox')).json()['ofertas'] == []
    legacy = (await c.get(f'/juegos/{gid}/tiendas?plataforma=PC&moneda=CLP')).json()
    assert legacy['tiendas'] == result['ofertas']


@pytest.mark.asyncio
async def test_legacy_classification_preserves_price_and_date_and_assigns_id(env):
    c, db, gid, gid2, tid = env
    await admin(env)
    old_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    await db.juegos.update_one({'_id': ObjectId(gid)}, {'$set': {'precios.0.fechaActualizacion': old_date}})
    before = (await c.get(f'/juegos/{gid}')).json()['precios']
    r = await c.put(f'/juegos/{gid}/tiendas/{tid}?sin_plataforma=true&moneda=CLP', json={'plataforma': 'PC'})
    assert r.status_code == 200, r.text
    changed, untouched = r.json()['precios']
    assert ObjectId.is_valid(changed['ofertaId'])
    assert changed['precio'] == before[0]['precio'] and changed['fechaActualizacion'] == before[0]['fechaActualizacion']
    assert changed['plataforma'] == 'PC' and untouched == before[1]
    stored_before = await db.juegos.find_one({'_id': ObjectId(gid)})
    await c.get(f'/juegos/{gid}/ofertas')
    assert await db.juegos.find_one({'_id': ObjectId(gid)}) == stored_before


@pytest.mark.asyncio
async def test_duplicate_on_update_is_rejected_without_changing_prices(env):
    c, db, gid, tid = await admin(env)
    await add(c, gid, tid)
    ps5 = await add(c, gid, tid, 'PS5')
    usd = await add(c, gid, tid, currency='USD')
    before = await db.juegos.find_one({'_id': ObjectId(gid)})
    for oid, body in [(ps5['ofertaId'], {'plataforma': 'PC'}), (usd['ofertaId'], {'moneda': 'CLP'})]:
        assert (await c.put(f'/juegos/{gid}/ofertas/{oid}', json=body)).status_code == 409
    assert (await c.post(f'/juegos/{gid}/ofertas', json={'tiendaId': tid, 'plataforma': 'PC', 'precio': 10})).status_code == 409
    assert await db.juegos.find_one({'_id': ObjectId(gid)}) == before


@pytest.mark.asyncio
async def test_legacy_selectors_are_exact_and_ambiguous_update_is_not_applied(env):
    c, db, gid, tid = await admin(env)
    await add(c, gid, tid)
    await add(c, gid, tid, currency='USD', price=10)
    await add(c, gid, tid, 'PS5')
    assert (await c.put(f'/juegos/{gid}/tiendas/{tid}?plataforma=PC', json={'precio': 1})).status_code == 409
    r = await c.put(f'/juegos/{gid}/tiendas/{tid}?plataforma=PC&moneda=USD', json={'precio': 12})
    assert r.status_code == 200
    assert [p['precio'] for p in r.json()['precios']] == [20000, 12, 20000]
    assert (await c.delete(f'/juegos/{gid}/tiendas/{tid}?plataforma=PC&moneda=USD')).status_code == 200
    assert len((await c.get(f'/juegos/{gid}')).json()['precios']) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize('body', [{}, {'precio': None}, {'moneda': None}, {'precio': -1}, {'plataforma': 'Switch'}, {'tiendaId': '123'}, {'precio': 1, 'campoDesconocido': True}])
async def test_invalid_partial_updates_are_rejected(env, body):
    c, db, gid, tid = await admin(env)
    offer = await add(c, gid, tid)
    assert (await c.put(f"/juegos/{gid}/ofertas/{offer['ofertaId']}", json=body)).status_code == 422


@pytest.mark.asyncio
async def test_new_create_requires_platform_and_checks_permissions_and_resource(env):
    c, db, gid, gid2, tid = env
    assert (await c.post(f'/juegos/{gid2}/ofertas', json={'tiendaId': tid, 'plataforma': 'PS5', 'precio': 1})).status_code == 401
    u = await register(c)
    await login(c)
    oid = str(ObjectId())
    assert (await c.post(f'/juegos/{gid2}/ofertas', json={'tiendaId': tid, 'plataforma': 'PS5', 'precio': 1})).status_code == 403
    assert (await c.put(f'/juegos/{gid2}/ofertas/{oid}', json={'precio': 1})).status_code == 403
    assert (await c.delete(f'/juegos/{gid2}/ofertas/{oid}')).status_code == 403
    await db.usuarios.update_one({'_id': ObjectId(u['_id'])}, {'$set': {'rol': 'admin'}})
    assert (await c.post(f'/juegos/{gid2}/ofertas', json={'tiendaId': tid, 'precio': 1})).status_code == 422
    assert (await c.post(f'/juegos/{gid2}/ofertas', json={'tiendaId': str(ObjectId()), 'plataforma': 'PS5', 'precio': 1})).status_code == 404
    offer = await add(c, gid2, tid, 'PS5')
    assert (await c.put(f"/juegos/{gid}/ofertas/{offer['ofertaId']}", json={'precio': 1})).status_code == 404
    assert (await c.delete(f'/juegos/{gid2}/ofertas/{oid}')).status_code == 404
    assert (await c.delete(f'/juegos/{gid2}/ofertas/invalido')).status_code == 400


@pytest.mark.asyncio
async def test_filter_validation_and_concurrent_duplicate_creation(env):
    c, db, gid, tid = await admin(env)
    for query in ['plataforma=PC&sin_plataforma=true', 'moneda=clp', 'plataforma=']:
        assert (await c.get(f'/juegos/{gid}/ofertas?{query}')).status_code == 422
    data = {'tiendaId': tid, 'plataforma': 'PC', 'precio': 0, 'moneda': 'CLP'}
    results = await asyncio.gather(c.post(f'/juegos/{gid}/ofertas', json=data), c.post(f'/juegos/{gid}/ofertas', json=data))
    assert sorted(r.status_code for r in results) == [201, 409]
    assert len((await c.get(f'/juegos/{gid}/ofertas')).json()['ofertas']) == 1
