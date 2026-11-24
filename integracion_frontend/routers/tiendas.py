from fastapi import APIRouter, Depends, HTTPException, Query
from integracion_frontend.database import get_db
from integracion_frontend.security import get_admin
from integracion_frontend.schemas import TiendaWrite
from integracion_frontend.services.common import validar_id, serializar
from integracion_frontend.services.ofertas import auditar

router = APIRouter(prefix='/tiendas', tags=['Tiendas'])

@router.get('/')
async def listar_tiendas(plataforma: str | None = Query(None, min_length=1, max_length=100), db=Depends(get_db)):
    query = {'plataformas': plataforma} if plataforma is not None else {}
    return serializar(await db.tiendas.find(query).sort('nombre', 1).to_list(length=1000))

@router.get('/{tienda_id}')
async def obtener_tienda(tienda_id: str, db=Depends(get_db)):
    store = await db.tiendas.find_one({'_id': validar_id(tienda_id)})
    if not store:
        raise HTTPException(404, 'Tienda no encontrada')
    return serializar(store)

@router.post('/', status_code=201)
async def crear_tienda(datos: TiendaWrite, db=Depends(get_db), actual=Depends(get_admin)):
    doc = datos.model_dump()
    await db.tiendas.insert_one(doc)
    await auditar(db, actual, 'crear_tienda', str(doc['_id']))
    return serializar(doc)

@router.put('/{tienda_id}')
async def actualizar_tienda(tienda_id: str, datos: TiendaWrite, db=Depends(get_db), actual=Depends(get_admin)):
    oid = validar_id(tienda_id)
    if not await db.tiendas.find_one({'_id': oid}):
        raise HTTPException(404, 'Tienda no encontrada')
    cambios = datos.model_dump(exclude_unset=True)
    plataformas = cambios.get('plataformas')
    if plataformas is not None:
        incompatibles = {'precios': {'$elemMatch': {
            'tiendaId': {'$in': [oid, str(oid)]},
            'plataforma': {'$exists': True, '$nin': [None, '', *plataformas]},
        }}}
        if await db.juegos.count_documents(incompatibles):
            raise HTTPException(409, 'La tienda tiene ofertas en otras plataformas. Corrige esas ofertas antes de restringir sus plataformas')
    result = await db.tiendas.update_one({'_id': oid}, {'$set': cambios})
    if not result.matched_count:
        raise HTTPException(404, 'Tienda no encontrada')
    await auditar(db, actual, 'editar_tienda', tienda_id)
    return serializar(await db.tiendas.find_one({'_id': validar_id(tienda_id)}))

@router.delete('/{tienda_id}')
async def eliminar_tienda(tienda_id: str, db=Depends(get_db), actual=Depends(get_admin)):
    oid = validar_id(tienda_id)
    if await db.juegos.count_documents({'precios.tiendaId': {'$in': [oid, tienda_id]}}):
        raise HTTPException(409, 'La tienda tiene ofertas asociadas y no puede eliminarse')
    result = await db.tiendas.delete_one({'_id': oid})
    if not result.deleted_count:
        raise HTTPException(404, 'Tienda no encontrada')
    await auditar(db, actual, 'eliminar_tienda', tienda_id)
    return {'mensaje': 'Tienda eliminada'}
