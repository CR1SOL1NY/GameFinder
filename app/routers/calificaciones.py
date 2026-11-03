"""Calificaciones: GET/POST públicos; PUT/DELETE requieren JWT."""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/calificaciones", tags=["Calificaciones"])


def serializar(valor):
    return jsonable_encoder(valor, custom_encoder={ObjectId: str})


def validar_id(valor: str):
    if not ObjectId.is_valid(valor):
        raise HTTPException(status_code=400, detail="Formato de ID inválido")
    return ObjectId(valor)


class CalificacionCreate(BaseModel):
    usuarioId: str
    juegoId: str
    puntaje: int = Field(ge=1, le=5)
    comentario: str


class CalificacionUpdate(BaseModel):
    puntaje: int | None = Field(default=None, ge=1, le=5)
    comentario: str | None = None


@router.get("/juego/{juego_id}")
async def obtener_calificaciones_juego(juego_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    oid = validar_id(juego_id)
    reseñas = await db.calificaciones.find({"juegoId": oid}).sort("fecha", -1).to_list(length=100)
    return serializar(reseñas)


@router.post("/", status_code=201)
async def crear_calificacion(datos: CalificacionCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    usuario_oid, juego_oid = validar_id(datos.usuarioId), validar_id(datos.juegoId)
    if not await db.usuarios.find_one({"_id": usuario_oid}):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not await db.juegos.find_one({"_id": juego_oid}):
        raise HTTPException(status_code=404, detail="Juego no encontrado")
    documento = {
        "usuarioId": usuario_oid, "juegoId": juego_oid,
        "puntaje": datos.puntaje, "comentario": datos.comentario,
        "fecha": datetime.now(timezone.utc), "visible": True,
    }
    resultado = await db.calificaciones.insert_one(documento)
    return serializar(await db.calificaciones.find_one({"_id": resultado.inserted_id}))


@router.put("/{calificacion_id}")
async def modificar_calificacion(
    calificacion_id: str,
    datos: CalificacionUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    usuario_actual: dict = Depends(get_current_user),
):
    oid = validar_id(calificacion_id)
    cambios = datos.model_dump(exclude_unset=True)
    if not cambios or any(v is None for v in cambios.values()):
        raise HTTPException(status_code=400, detail="Envía puntaje y/o comentario válidos")
    cambios["fecha"] = datetime.now(timezone.utc)
    resultado = await db.calificaciones.update_one({"_id": oid}, {"$set": cambios})
    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Calificación no encontrada")
    return serializar(await db.calificaciones.find_one({"_id": oid}))


@router.delete("/{calificacion_id}")
async def eliminar_calificacion(
    calificacion_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    usuario_actual: dict = Depends(get_current_user),
):
    resultado = await db.calificaciones.delete_one({"_id": validar_id(calificacion_id)})
    if resultado.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Calificación no encontrada")
    return {"mensaje": "Calificación eliminada exitosamente", "calificacionId": calificacion_id}
