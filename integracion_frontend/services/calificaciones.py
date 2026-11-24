from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
from integracion_frontend.services.common import serializar, validar_id


async def crear(db, juego_id, datos, actual):
    uid = ObjectId(actual['_id'])
    if datos.usuarioId is not None and str(uid) != datos.usuarioId:
        raise HTTPException(403, 'Solo puedes publicar tus propias calificaciones')
    gid = validar_id(juego_id)
    if not await db.juegos.find_one({'_id': gid, 'activo': {'$ne': False}}):
        raise HTTPException(404, 'Juego no encontrado')
    if await db.calificaciones.find_one({'usuarioId': uid, 'juegoId': gid}):
        raise HTTPException(409, 'Ya calificaste este juego; puedes actualizar tu reseña')
    doc = {'usuarioId': uid, 'juegoId': gid, 'puntaje': datos.puntaje, 'comentario': datos.comentario.strip(), 'fecha': datetime.now(timezone.utc), 'visible': True}
    try:
        await db.calificaciones.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(409, 'Ya calificaste este juego')
    return serializar(doc)


async def listar(db, juego_id, skip=0, limit=50):
    gid = validar_id(juego_id)
    if not await db.juegos.find_one({'_id': gid, 'activo': {'$ne': False}}):
        raise HTTPException(404, 'Juego no encontrado')
    rows = await db.calificaciones.find({'juegoId': gid, 'visible': {'$ne': False}}).sort([('fecha', -1), ('_id', 1)]).skip(skip).limit(limit).to_list(length=limit)
    users = await db.usuarios.find({'_id': {'$in': [r['usuarioId'] for r in rows]}}, {'nombre': 1}).to_list(length=limit)
    names = {u['_id']: u.get('nombre', 'Usuario') for u in users}
    for r in rows:
        r['nombreUsuario'] = names.get(r['usuarioId'], 'Usuario')
    return serializar(rows)
