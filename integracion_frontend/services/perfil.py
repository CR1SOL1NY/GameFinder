"""Lecturas del perfil; no modifica documentos ni prepara nuevos índices."""
from bson import ObjectId


async def juegos_de_resenas(db, rows):
    ids = [ObjectId(str(r['juegoId'])) for r in rows if ObjectId.is_valid(str(r.get('juegoId', '')))]
    games = {str(g['_id']): g async for g in db.juegos.find(
        {'_id': {'$in': ids}, 'activo': {'$ne': False}}, {'titulo': 1, 'imagenPortada': 1}
    )}
    return [{**r, 'juego': games.get(str(r.get('juegoId')))} for r in rows]


async def resumen_calificaciones(db, usuario_id):
    result = await db.calificaciones.aggregate([
        {'$match': {'usuarioId': usuario_id}},
        {'$facet': {
            'estadisticas': [{'$group': {'_id': None, 'total': {'$sum': 1}, 'promedio': {'$avg': '$puntaje'}}}],
            'ultimas': [{'$sort': {'fecha': -1, '_id': -1}}, {'$limit': 3}],
        }},
    ]).to_list(length=1)
    data = result[0] if result else {}
    stats = next(iter(data.get('estadisticas', [])), {'total': 0, 'promedio': None})
    return {'total': stats['total'], 'promedio': stats['promedio'], 'ultimas': await juegos_de_resenas(db, data.get('ultimas', []))}


async def precios_deseados(db, actual):
    """Instantánea de solo lectura de las ofertas de la lista propia, sin rastrear al usuario."""
    ids = list({ObjectId(str(d['juegoId'])) for d in actual.get('listaDeseados', []) if ObjectId.is_valid(str(d.get('juegoId', '')))})
    if not ids:
        return {'juegos': []}
    games = await db.juegos.find({'_id': {'$in': ids}, 'activo': {'$ne': False}}, {'titulo': 1, 'imagenPortada': 1, 'precios': 1}).to_list(length=len(ids))
    store_ids = list({ObjectId(str(p['tiendaId'])) for g in games for p in g.get('precios', []) if ObjectId.is_valid(str(p.get('tiendaId', '')))})
    stores = {str(t['_id']): t.get('nombre') async for t in db.tiendas.find({'_id': {'$in': store_ids}}, {'nombre': 1})}
    return {'juegos': [{**g, 'precios': [{**p, 'nombreTienda': stores.get(str(p.get('tiendaId')))} for p in g.get('precios', [])]} for g in games]}
