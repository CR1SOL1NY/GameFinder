"""Tiendas: consultas públicas; DELETE solo con JWT."""
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/tiendas", tags=["Tiendas"])


def validar_id(valor):
    if not ObjectId.is_valid(valor):
        raise HTTPException(status_code=400, detail="Formato de ID inválido")
    return ObjectId(valor)


@router.get("/")
async def listar_tiendas(db: AsyncIOMotorDatabase = Depends(get_db)):
    datos = await db.tiendas.find().to_list(length=100)
    return jsonable_encoder(datos, custom_encoder={ObjectId: str})


@router.get("/{tienda_id}")
async def obtener_tienda(tienda_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    tienda = await db.tiendas.find_one({"_id": validar_id(tienda_id)})
    if tienda is None:
        raise HTTPException(status_code=404, detail="Tienda no encontrada")
    return jsonable_encoder(tienda, custom_encoder={ObjectId: str})


@router.delete("/{tienda_id}")
async def eliminar_tienda(
    tienda_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    usuario_actual: dict = Depends(get_current_user),
):
    oid = validar_id(tienda_id)
    tienda = await db.tiendas.find_one({"_id": oid})
    if tienda is None:
        raise HTTPException(status_code=404, detail="Tienda no encontrada")
    asociados = await db.juegos.count_documents({"$or": [
        {"precios.tiendaId": oid}, {"precio_mas_barato.tiendaId": oid},
    ]})
    if asociados:
        raise HTTPException(
            status_code=409,
            detail=f"No se puede eliminar la tienda: está asociada a {asociados} videojuegos",
        )
    resultado = await db.tiendas.delete_one({"_id": oid})
    if resultado.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tienda no encontrada")
    return {"mensaje": "Tienda eliminada exitosamente", "tiendaId": tienda_id, "nombre": tienda["nombre"]}
