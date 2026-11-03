from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List
from app.database import get_db
from app.models import Juego, Calificacion

router = APIRouter(prefix="/juegos", tags=["Juegos"])

# --- LÓGICA DEL CATÁLOGO DE JUEGOS ---
@router.get("/", response_model=List[Juego])
async def listar_juegos(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), db: AsyncIOMotorDatabase = Depends(get_db)):
    """Obtiene el catálogo de juegos."""
    cursor = db.juegos.find().skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

@router.get("/buscar", response_model=List[Juego])
async def buscar_juegos(q: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Busca juegos por coincidencia en el título (ignora mayúsculas)."""
    cursor = db.juegos.find({"titulo": {"$regex": q, "$options": "i"}})
    resultados = await cursor.to_list(length=100)
    if not resultados:
        raise HTTPException(status_code=404, detail="No se encontraron juegos con ese título")
    return resultados

# Mantener esta ruta estática antes de /{id_juego}, que capturaría «estadisticas».
@router.get("/estadisticas/calificaciones")
async def estadisticas_juegos(db: AsyncIOMotorDatabase = Depends(get_db)):
    """Estadísticas agrupadas de los juegos."""
    pipeline = [
        {"$lookup": {
            "from": "calificaciones",
            "localField": "_id",
            "foreignField": "juegoId",
            "as": "reseñas"
        }},
        {"$project": {
            "titulo": 1,
            "total_reseñas": {"$size": "$reseñas"},
            "promedio_puntaje": {"$avg": "$reseñas.puntaje"}
        }},
        {"$match": {"total_reseñas": {"$gt": 0}}},
        {"$sort": {"promedio_puntaje": -1}}
    ]
    resultados = await db.juegos.aggregate(pipeline).to_list(length=100)
    for res in resultados:
        res["_id"] = str(res["_id"])
    return resultados

@router.get("/{id_juego}", response_model=Juego)
async def detalle_juego(id_juego: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Obtiene el detalle completo de un juego."""
    if not ObjectId.is_valid(id_juego):
        raise HTTPException(status_code=400, detail="Formato de ID inválido")
    juego = await db.juegos.find_one({"_id": ObjectId(id_juego)})
    if not juego:
        raise HTTPException(status_code=404, detail="Juego no encontrado")
    return juego

# --- LÓGICA DE CALIFICACIONES (RESEÑAS) ---
@router.get("/{id_juego}/calificaciones", response_model=List[Calificacion])
async def obtener_calificaciones_juego(id_juego: str, skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db: AsyncIOMotorDatabase = Depends(get_db)):
    """Obtiene reseñas de un juego específico."""
    if not ObjectId.is_valid(id_juego):
        raise HTTPException(status_code=400, detail="Formato de ID inválido")
    cursor = db.calificaciones.find({"juegoId": ObjectId(id_juego)}).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

@router.post("/{id_juego}/calificaciones", response_model=Calificacion)
async def agregar_calificacion(id_juego: str, calificacion_in: Calificacion, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Agrega una reseña a un juego."""
    if not ObjectId.is_valid(id_juego) or not ObjectId.is_valid(calificacion_in.usuarioId):
        raise HTTPException(status_code=400, detail="Formato de ID inválido para juego o usuario")
    if not await db.juegos.find_one({"_id": ObjectId(id_juego)}):
        raise HTTPException(status_code=404, detail="No puedes calificar un juego que no existe")
    if not await db.usuarios.find_one({"_id": ObjectId(calificacion_in.usuarioId)}):
        raise HTTPException(status_code=404, detail="El usuario no existe")

    cal_dict = calificacion_in.model_dump(by_alias=True, exclude={"id"})
    cal_dict["usuarioId"] = ObjectId(calificacion_in.usuarioId)
    cal_dict["juegoId"] = ObjectId(id_juego)
    resultado = await db.calificaciones.insert_one(cal_dict)
    return await db.calificaciones.find_one({"_id": resultado.inserted_id})

@router.delete("/{id_juego}")
async def eliminar_juego(
    id_juego: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Elimina un juego y sus referencias."""

    # 1. Validar ObjectId
    if not ObjectId.is_valid(id_juego):
        raise HTTPException(
            status_code=400,
            detail="Formato de ID inválido"
        )

    juego_id = ObjectId(id_juego)

    # 2. Verificar existencia
    juego = await db.juegos.find_one({"_id": juego_id})

    if not juego:
        raise HTTPException(
            status_code=404,
            detail="Juego no encontrado"
        )

    # 3. Eliminar sus calificaciones
    await db.calificaciones.delete_many({
        "juegoId": juego_id
    })

    # 4. Quitar de listas de deseados
    await db.usuarios.update_many(
        {"listaDeseados": juego_id},
        {"$pull": {"listaDeseados": juego_id}}
    )

    # 5. Eliminar juego
    await db.juegos.delete_one({
        "_id": juego_id
    })

    return {
        "mensaje": "Juego eliminado exitosamente",
        "juegoId": id_juego
    }