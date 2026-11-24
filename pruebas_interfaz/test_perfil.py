"""Resumen de perfil de solo lectura, con datos sintéticos aislados."""
from datetime import datetime, timedelta, timezone
import pytest
from bson import ObjectId
from pruebas_interfaz.conftest import register, login


@pytest.mark.asyncio
async def test_summary_requires_session_and_returns_empty_without_invented_average(env):
    c, db, gid, *_ = env
    assert (await c.get('/usuarios/me/resumen-calificaciones')).status_code == 401
    u = await register(c)
    await login(c)
    await db.calificaciones.insert_one({'usuarioId': ObjectId(), 'juegoId': ObjectId(gid), 'puntaje': 5, 'fecha': datetime.now(timezone.utc)})
    assert (await c.get('/usuarios/me/resumen-calificaciones')).json() == {'total': 0, 'promedio': None, 'ultimas': []}


@pytest.mark.asyncio
async def test_summary_uses_all_reviews_not_only_last_page_and_never_writes(env):
    c, db, *_ = env
    u = await register(c)
    await login(c)
    ids = [ObjectId() for _ in range(57)]
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    await db.juegos.insert_many([{'_id': gid, 'titulo': f'Juego sintético {i}', 'imagenPortada': 'https://example.com/fixture.jpg'} for i, gid in enumerate(ids)])
    await db.calificaciones.insert_many([{'usuarioId': ObjectId(u['_id']), 'juegoId': gid, 'puntaje': 5 if i < 54 else 1, 'comentario': f'Reseña sintética {i}', 'fecha': base + timedelta(days=i)} for i, gid in enumerate(ids)])
    await db.calificaciones.insert_one({'usuarioId': ObjectId(), 'juegoId': ids[0], 'puntaje': 1, 'comentario': 'No debe mostrarse', 'fecha': base + timedelta(days=100)})
    before = {name: await db[name].find().to_list(length=None) for name in await db.list_collection_names()}
    response = await c.get('/usuarios/me/resumen-calificaciones')
    assert response.status_code == 200, response.text
    summary = response.json()
    assert summary['total'] == 57
    assert summary['promedio'] == pytest.approx((54 * 5 + 3) / 57)
    assert [r['juego']['titulo'] for r in summary['ultimas']] == ['Juego sintético 56', 'Juego sintético 55', 'Juego sintético 54']
    assert all(r['usuarioId'] == u['_id'] for r in summary['ultimas'])
    assert all(set(r['juego']) == {'_id', 'titulo', 'imagenPortada'} for r in summary['ultimas'])
    page1 = (await c.get('/usuarios/me/calificaciones')).json()
    page2 = (await c.get('/usuarios/me/calificaciones?skip=50')).json()
    assert len(page1) == 50 and len(page2) == 7
    assert page1[0]['juego']['titulo'] == 'Juego sintético 56'
    assert not {r['_id'] for r in page1} & {r['_id'] for r in page2}
    after = {name: await db[name].find().to_list(length=None) for name in await db.list_collection_names()}
    assert after == before


@pytest.mark.asyncio
async def test_summary_is_private_and_handles_missing_or_hidden_games(env):
    c, db, gid, gid2, _ = env
    ana = await register(c)
    await login(c)
    await db.juegos.update_one({'_id': ObjectId(gid2)}, {'$set': {'activo': False}})
    missing = ObjectId()
    await db.calificaciones.insert_many([
        {'usuarioId': ObjectId(ana['_id']), 'juegoId': ObjectId(gid2), 'puntaje': 4, 'visible': False, 'fecha': datetime(2026, 1, 1)},
        {'usuarioId': ObjectId(ana['_id']), 'juegoId': missing, 'puntaje': 2, 'fecha': datetime(2026, 1, 2)},
    ])
    summary = (await c.get('/usuarios/me/resumen-calificaciones')).json()
    assert summary['total'] == 2 and summary['promedio'] == 3
    assert all(r['juego'] is None for r in summary['ultimas'])
    # Los parámetros no permiten elegir la cuenta de otra persona.
    other = await register(c, 'otra@example.com')
    await login(c, 'otra@example.com')
    assert (await c.get('/usuarios/me/resumen-calificaciones', params={'usuarioId': ana['_id']})).json() == {'total': 0, 'promedio': None, 'ultimas': []}
