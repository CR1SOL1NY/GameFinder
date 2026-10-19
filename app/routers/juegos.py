from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List
from app.database import get_db
from app.models import Juego, Calificacion

router = APIRouter(prefix="/juegos", tags=["Juegos"])

# --- LÓGICA DEL CATÁLOGO DE JUEGOS ---

@router.get("/", response_model=List[Juego])
async def listar_juegos(skip: int = 0, limit: int = 100, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Obtiene el catálogo de juegos."""
    cursor = db.juegos.find().skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

@router.get("/buscar", response_model=List[Juego])
async def buscar_juegos(q: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Busca juegos por coincidencia en el título (Ignora mayúsculas y minúsculas)."""
    cursor = db.juegos.find({"titulo": {"$regex": q, "$options": "i"}})
    resultados = await cursor.to_list(length=100)
    if not resultados:
        raise HTTPException(status_code=404, detail="No se encontraron juegos con ese título")
    return resultados

@router.get("/{id_juego}", response_model=Juego)
async def detalle_juego(id_juego: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Obtiene el detalle completo de un juego, incluyendo sus tiendas y plataformas embebidas."""
    if not ObjectId.is_valid(id_juego):
        raise HTTPException(status_code=400, detail="Formato de ID inválido")
        
    juego = await db.juegos.find_one({"_id": ObjectId(id_juego)})
    if not juego:
        raise HTTPException(status_code=404, detail="Juego no encontrado")
    return juego


# --- LÓGICA DE CALIFICACIONES (RESEÑAS) ---

@router.get("/{id_juego}/calificaciones", response_model=List[Calificacion])
async def obtener_calificaciones_juego(id_juego: str, skip: int = 0, limit: int = 50, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Obtiene todas las reseñas que la comunidad le ha dejado a un juego específico."""
    if not ObjectId.is_valid(id_juego):
        raise HTTPException(status_code=400, detail="Formato de ID inválido")
    
    # Buscamos en la colección 'calificaciones' aquellas cuyo 'id_juego' coincida
    cursor = db.calificaciones.find({"id_juego": id_juego}).skip(skip).limit(limit)
    calificaciones = await cursor.to_list(length=limit)
    return calificaciones

@router.post("/{id_juego}/calificaciones", response_model=Calificacion)
async def agregar_calificacion(id_juego: str, calificacion_in: Calificacion, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Agrega una nueva reseña a un juego. El JSON de entrada debe traer el id_usuario, puntaje y comentario."""
    if not ObjectId.is_valid(id_juego) or not ObjectId.is_valid(calificacion_in.id_usuario):
        raise HTTPException(status_code=400, detail="Formato de ID inválido para juego o usuario")
    
    # 1. Validamos que el juego exista
    juego_existe = await db.juegos.find_one({"_id": ObjectId(id_juego)})
    if not juego_existe:
        raise HTTPException(status_code=404, detail="No puedes calificar un juego que no existe")
        
    # 2. Validamos que el usuario que intenta calificar exista
    usuario_existe = await db.usuarios.find_one({"_id": ObjectId(calificacion_in.id_usuario)})
    if not usuario_existe:
        raise HTTPException(status_code=404, detail="El usuario no existe")

    # 3. Preparamos y guardamos el documento
    cal_dict = calificacion_in.model_dump(by_alias=True, exclude={"id"})
    cal_dict["id_juego"] = id_juego # Forzamos el ID de la URL por seguridad
    
    resultado = await db.calificaciones.insert_one(cal_dict)
    nueva_calificacion = await db.calificaciones.find_one({"_id": resultado.inserted_id})
    return nueva_calificacion