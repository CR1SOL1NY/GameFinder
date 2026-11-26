"""Rutas originales conservadas y catálogo ampliado con filtros del servidor."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from integracion_frontend.database import get_db
from integracion_frontend.security import get_admin, get_current_user
from integracion_frontend.schemas import CalificacionJuegoCreate, OfertaCreate, OfertaUpdate, OfertaPlataformaCreate, OfertaPorIdUpdate, JuegoWrite
from integracion_frontend.services.common import validar_id, serializar
from integracion_frontend.services.catalogo import catalogo, agregar_promedios
from integracion_frontend.services.calificaciones import crear, listar
from integracion_frontend.services.ofertas import cambiar_oferta, consultar_ofertas, auditar
from integracion_frontend.limiter import limiter

router = APIRouter(prefix='/juegos', tags=['Juegos'])

@router.get('/catalogo')
async def pagina_catalogo(q: str = Query('', max_length=150), genero: list[str] | None = Query(None), plataforma: list[str] | None = Query(None), precio_min: float | None = Query(None, ge=0, allow_inf_nan=False), precio_max: float | None = Query(None, ge=0, allow_inf_nan=False), orden: Literal['titulo', 'titulo_desc', 'precio', 'precio_desc', 'fecha'] = 'titulo', skip: int = Query(0, ge=0, le=1000000), limit: int = Query(24, ge=1, le=100), db=Depends(get_db)):
    if precio_min is not None and precio_max is not None and precio_min > precio_max:
        raise HTTPException(422, 'El precio mínimo supera al máximo')
    return await catalogo(db, skip, limit, q=q, genero=genero, plataforma=plataforma, precio_min=precio_min, precio_max=precio_max, sort=orden)

@router.get('/filtros')
async def opciones_filtros(db=Depends(get_db)):
    active = {'activo': {'$ne': False}}
    return {'generos': sorted(x for x in await db.juegos.distinct('generos', active) if isinstance(x, str)), 'plataformas': sorted(x for x in await db.juegos.distinct('plataformas', active) if isinstance(x, str))}

@router.get('/')
@limiter.limit('100/minute')
async def listar_juegos(request: Request, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), db=Depends(get_db)):
    return (await catalogo(db, skip, limit))['items']

@router.get('/buscar')
async def buscar_juegos(q: str = Query(..., min_length=1, max_length=150), db=Depends(get_db)):
    return (await catalogo(db, limit=100, q=q))['items']

@router.get('/estadisticas/calificaciones')
async def estadisticas_juegos(db=Depends(get_db)):
    stats = await db.calificaciones.aggregate([{'$match': {'visible': {'$ne': False}}}, {'$group': {'_id': '$juegoId', 'total_reseñas': {'$sum': 1}, 'promedio_puntaje': {'$avg': '$puntaje'}}}, {'$sort': {'promedio_puntaje': -1}}, {'$limit': 100}]).to_list(length=100)
    return serializar(stats)

@router.post('/', status_code=201)
async def crear_juego(datos: JuegoWrite, db=Depends(get_db), actual=Depends(get_admin)):
    doc = {**datos.model_dump(), 'precios': [], 'precio_mas_barato': None}
    validar_plataforma_requisitos(doc)
    await db.juegos.insert_one(doc)
    await auditar(db, actual, 'crear_juego', str(doc['_id']))
    return serializar(doc)

@router.get('/{id_juego}')
async def detalle_juego(id_juego: str, db=Depends(get_db)):
    game = await db.juegos.find_one({'_id': validar_id(id_juego), 'activo': {'$ne': False}})
    if not game:
        raise HTTPException(404, 'Juego no encontrado')
    return (await agregar_promedios(db, [game]))[0]

@router.put('/{id_juego}')
async def editar_juego(id_juego: str, datos: JuegoWrite, db=Depends(get_db), actual=Depends(get_admin)):
    juego_id = validar_id(id_juego)
    anterior = await db.juegos.find_one({'_id': juego_id})
    if not anterior:
        raise HTTPException(404, 'Juego no encontrado')
    # Omitir un campo conserva su valor: clientes anteriores no borran los nuevos datos.
    cambios = datos.model_dump(exclude_unset=True)
    comprobar_plataformas = bool({'plataformas', 'requisitosSistema'} & cambios.keys())
    selector = {'_id': juego_id}
    if comprobar_plataformas:
        validar_plataforma_requisitos({**anterior, **cambios})
        selector.update({campo: anterior.get(campo) for campo in ('plataformas', 'requisitosSistema')})
    result = await db.juegos.update_one(selector, {'$set': cambios})
    if not result.matched_count:
        raise HTTPException(409, 'La información del juego cambió; vuelve a cargarla antes de guardar')
    await auditar(db, actual, 'editar_juego', id_juego)
    return serializar(await db.juegos.find_one({'_id': validar_id(id_juego)}))


def validar_plataforma_requisitos(juego):
    requisitos = juego.get('requisitosSistema')
    if isinstance(requisitos, dict) and requisitos.get('plataforma') and requisitos['plataforma'] not in juego.get('plataformas', []):
        raise HTTPException(422, 'La plataforma de los requisitos debe estar registrada en el videojuego')

@router.delete('/{id_juego}')
async def eliminar_juego(id_juego: str, db=Depends(get_db), actual=Depends(get_admin)):
    result = await db.juegos.update_one({'_id': validar_id(id_juego)}, {'$set': {'activo': False}})
    if not result.matched_count:
        raise HTTPException(404, 'Juego no encontrado')
    await auditar(db, actual, 'desactivar_juego', id_juego)
    return {'mensaje': 'Juego desactivado; sus datos se conservan'}

@router.get('/{id_juego}/calificaciones')
async def obtener_calificaciones_juego(id_juego: str, skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db=Depends(get_db)):
    return await listar(db, id_juego, skip, limit)

@router.post('/{id_juego}/calificaciones', status_code=201)
async def agregar_calificacion(id_juego: str, datos: CalificacionJuegoCreate, db=Depends(get_db), actual=Depends(get_current_user)):
    return await crear(db, id_juego, datos, actual)

@router.get('/{id_juego}/ofertas')
async def ofertas_por_plataforma(id_juego: str, plataforma: str | None = Query(None, min_length=1, max_length=100), moneda: str | None = Query(None, pattern=r'^[A-Z]{3}$'), sin_plataforma: bool = False, db=Depends(get_db)):
    """Ofertas y mínimos por plataforma/moneda; las asociaciones ausentes no se infieren.

    `ofertas` y `resumen` corresponden a los filtros aplicados. `plataformas` y
    `monedas` describen el juego completo. No modifica documentos antiguos.
    """
    return await consultar_ofertas(db, id_juego, plataforma, moneda, sin_plataforma)

@router.post('/{id_juego}/ofertas', status_code=201)
async def crear_oferta_plataforma(id_juego: str, datos: OfertaPlataformaCreate, db=Depends(get_db), actual=Depends(get_admin)):
    return await cambiar_oferta(db, id_juego, datos.tiendaId, actual, 'agregar', datos.model_dump())

@router.put('/{id_juego}/ofertas/{oferta_id}')
async def editar_oferta_individual(id_juego: str, oferta_id: str, datos: OfertaPorIdUpdate, db=Depends(get_db), actual=Depends(get_admin)):
    return await cambiar_oferta(db, id_juego, None, actual, 'actualizar', datos.model_dump(exclude_unset=True), oferta_id=oferta_id)

@router.delete('/{id_juego}/ofertas/{oferta_id}')
async def quitar_oferta_individual(id_juego: str, oferta_id: str, db=Depends(get_db), actual=Depends(get_admin)):
    return await cambiar_oferta(db, id_juego, None, actual, 'quitar', oferta_id=oferta_id)

@router.get('/{id_juego}/tiendas')
async def obtener_tiendas_juego(id_juego: str, plataforma: str | None = Query(None, min_length=1, max_length=100), moneda: str | None = Query(None, pattern=r'^[A-Z]{3}$'), sin_plataforma: bool = False, db=Depends(get_db)):
    result = await consultar_ofertas(db, id_juego, plataforma, moneda, sin_plataforma)
    return {'juegoId': result['juegoId'], 'titulo': result['titulo'], 'totalTiendas': result['totalOfertas'], 'tiendas': result['ofertas']}

@router.post('/{id_juego}/tiendas', status_code=201)
async def agregar_tienda_a_juego(id_juego: str, datos: OfertaCreate, db=Depends(get_db), actual=Depends(get_admin)):
    return await cambiar_oferta(db, id_juego, datos.tiendaId, actual, 'agregar', datos.model_dump())

@router.put('/{id_juego}/tiendas/{tienda_id}')
async def actualizar_precio_tienda(id_juego: str, tienda_id: str, datos: OfertaUpdate, plataforma: str | None = Query(None, min_length=1, max_length=100), moneda: str | None = Query(None, pattern=r'^[A-Z]{3}$'), sin_plataforma: bool = False, db=Depends(get_db), actual=Depends(get_admin)):
    if datos.tiendaId is not None and datos.tiendaId != tienda_id:
        raise HTTPException(422, 'La tienda del cuerpo no coincide con la ruta')
    return await cambiar_oferta(db, id_juego, tienda_id, actual, 'actualizar', {k: v for k, v in datos.model_dump(exclude_unset=True).items() if k != 'tiendaId'}, plataforma, moneda, sin_plataforma)

@router.delete('/{id_juego}/tiendas/{tienda_id}')
async def eliminar_tienda_de_juego(id_juego: str, tienda_id: str, plataforma: str | None = Query(None, min_length=1, max_length=100), moneda: str | None = Query(None, pattern=r'^[A-Z]{3}$'), sin_plataforma: bool = False, db=Depends(get_db), actual=Depends(get_admin)):
    return await cambiar_oferta(db, id_juego, tienda_id, actual, 'quitar', plataforma=plataforma, moneda=moneda, sin_plataforma=sin_plataforma)
