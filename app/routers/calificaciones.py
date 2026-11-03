from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from app.database import get_db
from app.models import Calificacion
from typing import List
# Esquema de entrada compatible con los campos reales de Atlas.
class CalificacionCreate(BaseModel):
    usuarioId: str
    juegoId: str
    puntaje: int = Field(ge=1, le=5, description="El puntaje debe ser entre 1 y 5")
    comentario: str
    model_config = ConfigDict(populate_by_name=True)

router = APIRouter(prefix="/calificaciones", tags=["Calificaciones"])

@router.get("/juego/{juego_id}", response_model=List[Calificacion])
async def obtener_calificaciones_juego(juego_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Obtiene todas las reseñas de un juego, de la más reciente a la más antigua."""
    if not ObjectId.is_valid(juego_id):
        raise HTTPException(status_code=400, detail="Formato de ID de juego inválido")
    cursor = db.calificaciones.find({"juegoId": ObjectId(juego_id)}).sort("fecha", -1)
    calificaciones_bd = await cursor.to_list(length=100)
    for c in calificaciones_bd:
        c["_id"] = str(c["_id"])
        c["usuarioId"] = str(c["usuarioId"])
        c["juegoId"] = str(c["juegoId"])
    return calificaciones_bd

@router.post("/", response_model=Calificacion)
async def crear_calificacion(calificacion: CalificacionCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Permite publicar una nueva reseña y puntaje para un juego."""
    if not ObjectId.is_valid(calificacion.usuarioId) or not ObjectId.is_valid(calificacion.juegoId):
        raise HTTPException(status_code=400, detail="Formato de IDs inválidos")
    if not await db.usuarios.find_one({"_id": ObjectId(calificacion.usuarioId)}):
        raise HTTPException(status_code=404, detail="El usuario no existe")
    if not await db.juegos.find_one({"_id": ObjectId(calificacion.juegoId)}):
        raise HTTPException(status_code=404, detail="El juego no existe")

    nueva_calificacion = {
        "usuarioId": ObjectId(calificacion.usuarioId),
        "juegoId": ObjectId(calificacion.juegoId),
        "puntaje": calificacion.puntaje,
        "comentario": calificacion.comentario,
        "fecha": datetime.now(timezone.utc),
        "visible": True
    }
    resultado = await db.calificaciones.insert_one(nueva_calificacion)
    creada = await db.calificaciones.find_one({"_id": resultado.inserted_id})
    creada["_id"] = str(creada["_id"])
    creada["usuarioId"] = str(creada["usuarioId"])
    creada["juegoId"] = str(creada["juegoId"])
    return creada

@router.delete("/{calificacion_id}")
async def eliminar_calificacion(
    calificacion_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Elimina una calificación por su ID."""

    # 1. Validar ObjectId
    if not ObjectId.is_valid(calificacion_id):
        raise HTTPException(
            status_code=400,
            detail="Formato de ID inválido"
        )

    # 2. Eliminar calificación
    resultado = await db.calificaciones.delete_one({
        "_id": ObjectId(calificacion_id)
    })

    # 3. Verificar resultado
    if resultado.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Calificación no encontrada"
        )

    return {
        "mensaje": "Calificación eliminada exitosamente",
        "calificacionId": calificacion_id
    }