"""Catálogo paginado; nunca compara monedas distintas ni usa mínimos obsoletos."""
import re
from integracion_frontend.services.common import serializar


def pipeline_catalogo(q='', genero=None, plataforma=None, precio_min=None, precio_max=None, sort='titulo'):
    query = {'activo': {'$ne': False}}
    if q.strip():
        query['$or'] = [{field: {'$regex': re.escape(q.strip()), '$options': 'i'}} for field in ('titulo', 'desarrollador', 'generos', 'plataformas')]
    if genero:
        query['generos'] = {'$in': genero}
    if plataforma:
        query['plataformas'] = {'$in': plataforma}
    pipeline = [{'$match': query}, {'$addFields': {'_preciosCLP': {'$map': {'input': {'$filter': {'input': {'$ifNull': ['$precios', []]}, 'as': 'p', 'cond': {'$and': [{'$eq': ['$$p.moneda', 'CLP']}, {'$isNumber': '$$p.precio'}, {'$gte': ['$$p.precio', 0]}]}}}, 'as': 'p', 'in': '$$p.precio'}}}}]
    pipeline.append({'$addFields': {'_precioCLP': {'$min': '$_preciosCLP'}, '_tituloOrden': {'$toLower': '$titulo'}}})
    if precio_min is not None or precio_max is not None:
        price = {'$ne': None}
        if precio_min is not None:
            price['$gte'] = precio_min
        if precio_max is not None:
            price['$lte'] = precio_max
        pipeline.append({'$match': {'_precioCLP': price}})
    pipeline.append({'$addFields': {'_sinPrecio': {'$cond': [{'$eq': [{'$size': '$_preciosCLP'}, 0]}, 1, 0]}}})
    sorting = {'titulo': {'_tituloOrden': 1, '_id': 1}, 'titulo_desc': {'_tituloOrden': -1, '_id': 1}, 'precio': {'_sinPrecio': 1, '_precioCLP': 1, '_id': 1}, 'precio_desc': {'_sinPrecio': 1, '_precioCLP': -1, '_id': 1}, 'fecha': {'fechaLanzamiento': -1, '_id': 1}}
    pipeline.append({'$sort': sorting[sort]})
    return pipeline


async def agregar_promedios(db, juegos):
    ids = [j['_id'] for j in juegos]
    rows = await db.calificaciones.aggregate([{'$match': {'juegoId': {'$in': ids}, 'visible': {'$ne': False}}}, {'$group': {'_id': '$juegoId', 'promedio': {'$avg': '$puntaje'}, 'total': {'$sum': 1}}}]).to_list(length=len(ids)) if ids else []
    stats = {r['_id']: r for r in rows}
    for juego in juegos:
        stat = stats.get(juego['_id'], {})
        juego['promedioCalificaciones'] = stat.get('promedio', 0)
        juego['totalCalificaciones'] = stat.get('total', 0)
        for k in ('_preciosCLP', '_precioCLP', '_tituloOrden', '_sinPrecio'):
            juego.pop(k, None)
    return serializar(juegos)


async def catalogo(db, skip=0, limit=24, **filters):
    pipeline = pipeline_catalogo(**filters)
    pipeline.append({'$facet': {'items': [{'$skip': skip}, {'$limit': limit}], 'metadata': [{'$count': 'total'}]}})
    result = await db.juegos.aggregate(pipeline).to_list(length=1)
    page = result[0] if result else {'items': [], 'metadata': []}
    return {'items': await agregar_promedios(db, page['items']), 'total': page['metadata'][0]['total'] if page['metadata'] else 0, 'skip': skip, 'limit': limit}
