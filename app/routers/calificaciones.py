from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List
from datetime import datetime
from pydantic import BaseModel, Field
from app.database import get_db

# Definimos el esquema de Pydantic para cuando un usuario envíe una nueva reseña
class CalificacionCreate(BaseModel):
    id_usuario: str
    id_juego: str
    puntaje: int = Field(ge=1, le=5, description="El puntaje debe ser entre 1 y 5")
    comentario: str

# Inicializamos el Router
router = APIRouter(prefix="/calificaciones", tags=["Calificaciones"])

@router.get("/juego/{juego_id}")
async def obtener_calificaciones_juego(juego_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Obtiene todas las reseñas de un juego específico, ordenadas de la más reciente a la más antigua."""
    if not ObjectId.is_valid(juego_id):
        raise HTTPException(status_code=400, detail="Formato de ID de juego inválido")
    
    # Buscamos las calificaciones usando la referencia (id_juego)
    cursor = db.calificaciones.find({"id_juego": ObjectId(juego_id)}).sort("fecha", -1)
    calificaciones_bd = await cursor.to_list(length=100) # Límite de 100 para no saturar
    
    # Formateamos la respuesta para convertir los ObjectId a string (evita errores de Pydantic/JSON)
    resultado = []
    for c in calificaciones_bd:
        c["_id"] = str(c["_id"])
        c["id_usuario"] = str(c["id_usuario"])
        c["id_juego"] = str(c["id_juego"])
        resultado.append(c)
        
    return resultado

@router.post("/")
async def crear_calificacion(calificacion: CalificacionCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Permite a un usuario publicar una nueva reseña y puntaje para un juego."""
    if not ObjectId.is_valid(calificacion.id_usuario) or not ObjectId.is_valid(calificacion.id_juego):
        raise HTTPException(status_code=400, detail="Formato de IDs inválidos")
        
    # 1. Validar que el usuario y el juego realmente existan en la base de datos
    usuario_existe = await db.usuarios.find_one({"_id": ObjectId(calificacion.id_usuario)})
    if not usuario_existe:
        raise HTTPException(status_code=404, detail="El usuario no existe")
        
    juego_existe = await db.juegos.find_one({"_id": ObjectId(calificacion.id_juego)})
    if not juego_existe:
        raise HTTPException(status_code=404, detail="El juego no existe")

    # 2. Construir el documento a insertar
    nueva_calificacion = {
        "id_usuario": ObjectId(calificacion.id_usuario),
        "id_juego": ObjectId(calificacion.id_juego),
        "puntaje": calificacion.puntaje,
        "comentario": calificacion.comentario,
        "fecha": datetime.utcnow()
    }
    
    # 3. Guardar en la base de datos
    resultado = await db.calificaciones.insert_one(nueva_calificacion)
    
    # 4. Recuperar el documento creado para devolverlo en la respuesta
    calificacion_creada = await db.calificaciones.find_one({"_id": resultado.inserted_id})
    calificacion_creada["_id"] = str(calificacion_creada["_id"])
    calificacion_creada["id_usuario"] = str(calificacion_creada["id_usuario"])
    calificacion_creada["id_juego"] = str(calificacion_creada["id_juego"])
    
    return calificacion_creada