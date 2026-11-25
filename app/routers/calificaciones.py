"""Reseñas públicas visibles; escritura autenticada y limitada al autor."""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_db
from app.security import get_current_user, autor_resena
from integracion_frontend.services.calificaciones import crear, listar

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
    return await listar(db, juego_id, limit=100)


@router.post("/", status_code=201)
async def crear_calificacion(datos: CalificacionCreate, db: AsyncIOMotorDatabase = Depends(get_db),
                             usuario_actual=Depends(get_current_user)):
    return await crear(db, datos.juegoId, datos, usuario_actual)


@router.put("/{calificacion_id}")
async def modificar_calificacion(
    calificacion_id: str,
    datos: CalificacionUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    usuario_actual: dict = Depends(get_current_user),
):
    oid = validar_id(calificacion_id)
    actual = await db.calificaciones.find_one({"_id": oid})
    if not actual:
        raise HTTPException(404, "Calificación no encontrada")
    autor_resena(actual, usuario_actual)
    cambios = datos.model_dump(exclude_unset=True)
    if not cambios or any(v is None for v in cambios.values()):
        raise HTTPException(status_code=400, detail="Envía puntaje y/o comentario válidos")
    cambios["fecha"] = datetime.now(timezone.utc)
    resultado = await db.calificaciones.update_one({"_id": oid, "usuarioId": usuario_actual["_id"]}, {"$set": cambios})
    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Calificación no encontrada")
    return serializar(await db.calificaciones.find_one({"_id": oid}))


@router.delete("/{calificacion_id}")
async def eliminar_calificacion(
    calificacion_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    usuario_actual: dict = Depends(get_current_user),
):
    oid = validar_id(calificacion_id)
    actual = await db.calificaciones.find_one({"_id": oid})
    if not actual:
        raise HTTPException(404, "Calificación no encontrada")
    # La moderación permite eliminar; nunca reescribir la opinión de otra persona.
    if usuario_actual.get("rol") != "admin":
        autor_resena(actual, usuario_actual)
    resultado = await db.calificaciones.delete_one({"_id": oid, "usuarioId": actual["usuarioId"]})
    if resultado.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Calificación no encontrada")
    return {"mensaje": "Calificación eliminada exitosamente", "calificacionId": calificacion_id}
