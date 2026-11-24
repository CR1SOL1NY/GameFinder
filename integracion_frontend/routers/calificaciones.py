"""Lecturas públicas y escrituras autenticadas, limitadas al propietario."""
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from integracion_frontend.database import get_db
from integracion_frontend.security import get_current_user
from integracion_frontend.schemas import CalificacionCreate, CalificacionUpdate
from integracion_frontend.services.common import validar_id, serializar
from integracion_frontend.services.calificaciones import crear, listar
from integracion_frontend.limiter import limiter

router = APIRouter(prefix='/calificaciones', tags=['Calificaciones'])

@router.get('/mia/{juego_id}')
async def mi_calificacion(juego_id: str, db=Depends(get_db), actual=Depends(get_current_user)):
    return serializar(await db.calificaciones.find_one({'juegoId': validar_id(juego_id), 'usuarioId': actual['_id']}))

@router.get('/juego/{juego_id}')
async def obtener_calificaciones_juego(juego_id: str, skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db=Depends(get_db)):
    return await listar(db, juego_id, skip, limit)

@router.post('/', status_code=201)
@limiter.limit('20/minute')
async def crear_calificacion(request: Request, datos: CalificacionCreate, db=Depends(get_db), usuario_actual=Depends(get_current_user)):
    return await crear(db, datos.juegoId, datos, usuario_actual)

@router.put('/{calificacion_id}')
async def modificar_calificacion(calificacion_id: str, datos: CalificacionUpdate, db=Depends(get_db), usuario_actual=Depends(get_current_user)):
    oid = validar_id(calificacion_id)
    current = await db.calificaciones.find_one({'_id': oid})
    if not current:
        raise HTTPException(404, 'Calificación no encontrada')
    if str(current['usuarioId']) != str(usuario_actual['_id']):
        raise HTTPException(403, 'Solo puedes editar tus propias calificaciones')
    cambios = datos.model_dump(exclude_unset=True)
    if not cambios or any(v is None for v in cambios.values()):
        raise HTTPException(400, 'Envía puntaje y/o comentario válidos')
    cambios['fecha'] = datetime.now(timezone.utc)
    await db.calificaciones.update_one({'_id': oid, 'usuarioId': ObjectId(usuario_actual['_id'])}, {'$set': cambios})
    return serializar(await db.calificaciones.find_one({'_id': oid}))

@router.delete('/{calificacion_id}')
async def eliminar_calificacion(calificacion_id: str, db=Depends(get_db), usuario_actual=Depends(get_current_user)):
    oid = validar_id(calificacion_id)
    current = await db.calificaciones.find_one({'_id': oid})
    if not current:
        raise HTTPException(404, 'Calificación no encontrada')
    if str(current['usuarioId']) != str(usuario_actual['_id']):
        raise HTTPException(403, 'Solo puedes eliminar tus propias calificaciones')
    await db.calificaciones.delete_one({'_id': oid, 'usuarioId': ObjectId(usuario_actual['_id'])})
    return {'mensaje': 'Calificación eliminada'}
