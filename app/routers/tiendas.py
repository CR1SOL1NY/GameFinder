
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.database import get_db

router = APIRouter(
    prefix="/tiendas",
    tags=["Tiendas"]
)


# 1. MOSTRAR TODAS LAS TIENDAS
@router.get("/")
async def listar_tiendas(
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    cursor = db.tiendas.find()
    tiendas = await cursor.to_list(length=100)

    for tienda in tiendas:
        tienda["_id"] = str(tienda["_id"])

    return tiendas


# 2. BUSCAR TIENDA POR ID
@router.get("/{tienda_id}")
async def obtener_tienda(
    tienda_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if not ObjectId.is_valid(tienda_id):
        raise HTTPException(
            status_code=400,
            detail="Formato de ID inválido"
        )

    tienda = await db.tiendas.find_one({
        "_id": ObjectId(tienda_id)
    })

    if not tienda:
        raise HTTPException(
            status_code=404,
            detail="Tienda no encontrada"
        )

    tienda["_id"] = str(tienda["_id"])

    return tienda


# 3. ELIMINAR TIENDA
@router.delete("/{tienda_id}")
async def eliminar_tienda(
    tienda_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if not ObjectId.is_valid(tienda_id):
        raise HTTPException(
            status_code=400,
            detail="Formato de ID inválido"
        )

    tienda_oid = ObjectId(tienda_id)

    # Verificar que exista
    tienda = await db.tiendas.find_one({
        "_id": tienda_oid
    })

    if not tienda:
        raise HTTPException(
            status_code=404,
            detail="Tienda no encontrada"
        )

    # Verificar si algún juego utiliza esta tienda
    juegos_asociados = await db.juegos.count_documents({
        "$or": [
            {"precios.tiendaId": tienda_oid},
            {"precio_mas_barato.tiendaId": tienda_oid}
        ]
    })

    if juegos_asociados > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"No se puede eliminar esta tienda porque "
                f"está asociada a {juegos_asociados} videojuegos"
            )
        )

    # Eliminar la tienda
    resultado = await db.tiendas.delete_one({
        "_id": tienda_oid
    })

    if resultado.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Tienda no encontrada"
        )

    return {
        "mensaje": "Tienda eliminada exitosamente",
        "tiendaId": tienda_id,
        "nombre": tienda["nombre"]
    }
