"""Endpoints de juegos para la BD GameFinder (tiendas referenciadas por ObjectId).

No requiere modificar app.models. Mantiene las rutas del router original.
"""
from datetime import datetime, timezone
from typing import Literal

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_db
from app.security import get_current_user

from fastapi import Request
from app.limiter import limiter

from app.security import crear_access_token

router = APIRouter(prefix="/juegos", tags=["Juegos"])


def preparar_json(valor):
    """Convierte ObjectId (incluidos los anidados) y datetime a valores JSON."""
    return jsonable_encoder(valor, custom_encoder={ObjectId: str})


def validar_id(id_texto: str, entidad: str = "ID") -> ObjectId:
    if not ObjectId.is_valid(id_texto):
        raise HTTPException(status_code=400, detail=f"Formato de {entidad} inválido")
    return ObjectId(id_texto)


class CalificacionCreate(BaseModel):
    usuarioId: str
    puntaje: int = Field(ge=1, le=5)
    comentario: str = ""
    visible: bool = True


class TiendaJuegoCreate(BaseModel):
    tiendaId: str
    precio: float = Field(ge=0)
    moneda: Literal["CLP"] = "CLP"
    urlProducto: str


# Obtiene el precio mínimo del arreglo actualizado dentro del mismo update.
# Se presupone que todos los precios del juego están expresados en CLP.
def etapa_minimo():
    return {
        "$set": {
            "precio_mas_barato": {
                "$let": {
                    "vars": {
                        "menor": {
                            "$arrayElemAt": [
                                {"$sortArray": {"input": "$precios", "sortBy": {"precio": 1}}},
                                0,
                            ]
                        }
                    },
                    "in": {
                        "$cond": [
                            {"$eq": [{"$size": "$precios"}, 0]},
                            None,
                            {
                                "precio": "$$menor.precio",
                                "moneda": "$$menor.moneda",
                                "tiendaId": "$$menor.tiendaId",
                            },
                        ]
                    },
                }
            }
        }
    }


# --- CATÁLOGO ---
@router.get("/")
@limiter.limit("100/minute")
async def listar_juegos(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    pipeline = [
        {"$sort": {"_id": 1}},
        {"$skip": skip},
        {"$limit": limit},
        {"$lookup": {
            "from": "calificaciones", "localField": "_id",
            "foreignField": "juegoId", "as": "calificaciones",
        }},
        {"$addFields": {
            "promedioCalificaciones": {"$ifNull": [{"$avg": "$calificaciones.puntaje"}, 0]},
            "totalCalificaciones": {"$size": "$calificaciones"},
        }},
        {"$project": {"calificaciones": 0}},
    ]
    juegos = await db.juegos.aggregate(pipeline).to_list(length=limit)
    return preparar_json(juegos)


@router.get("/buscar")
async def buscar_juegos(q: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    juegos = await db.juegos.find({"titulo": {"$regex": q, "$options": "i"}}).to_list(length=100)
    if not juegos:
        raise HTTPException(status_code=404, detail="No se encontraron juegos con ese título")
    return preparar_json(juegos)


# Ruta estática ANTES de /{id_juego}.
@router.get("/estadisticas/calificaciones")
async def estadisticas_juegos(db: AsyncIOMotorDatabase = Depends(get_db)):
    pipeline = [
        {"$lookup": {
            "from": "calificaciones", "localField": "_id",
            "foreignField": "juegoId", "as": "resenas"
        }},
        {"$project": {
            "titulo": 1,
            "total_reseñas": {"$size": "$resenas"},
            "promedio_puntaje": {"$avg": "$resenas.puntaje"},
        }},
        {"$match": {"total_reseñas": {"$gt": 0}}},
        {"$sort": {"promedio_puntaje": -1}},
    ]
    return preparar_json(await db.juegos.aggregate(pipeline).to_list(length=100))


@router.get("/{id_juego}")
async def detalle_juego(id_juego: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    juego = await db.juegos.find_one({"_id": validar_id(id_juego, "ID de juego")})
    if juego is None:
        raise HTTPException(status_code=404, detail="Juego no encontrado")
    return preparar_json(juego)


# --- CALIFICACIONES DE UN JUEGO ---
@router.get("/{id_juego}/calificaciones")
async def obtener_calificaciones_juego(
    id_juego: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    oid = validar_id(id_juego, "ID de juego")
    cursor = db.calificaciones.find({"juegoId": oid}).sort("fecha", -1).skip(skip).limit(limit)
    return preparar_json(await cursor.to_list(length=limit))


@router.post("/{id_juego}/calificaciones", status_code=201)
async def agregar_calificacion(
    id_juego: str,
    calificacion_in: CalificacionCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    oid_juego = validar_id(id_juego, "ID de juego")
    oid_usuario = validar_id(calificacion_in.usuarioId, "ID de usuario")
    if not await db.juegos.find_one({"_id": oid_juego}):
        raise HTTPException(status_code=404, detail="No puedes calificar un juego que no existe")
    if not await db.usuarios.find_one({"_id": oid_usuario}):
        raise HTTPException(status_code=404, detail="El usuario no existe")
    documento = {
        "usuarioId": oid_usuario,
        "juegoId": oid_juego,
        "puntaje": calificacion_in.puntaje,
        "comentario": calificacion_in.comentario,
        "fecha": datetime.now(timezone.utc),
        "visible": calificacion_in.visible,
    }
    resultado = await db.calificaciones.insert_one(documento)
    return preparar_json(await db.calificaciones.find_one({"_id": resultado.inserted_id}))


# --- TIENDAS ASOCIADAS A UN JUEGO ---
@router.get("/{id_juego}/tiendas")
async def obtener_tiendas_juego(id_juego: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    oid = validar_id(id_juego, "ID de juego")
    juego = await db.juegos.find_one({"_id": oid}, {"titulo": 1})
    if juego is None:
        raise HTTPException(status_code=404, detail="Juego no encontrado")
    pipeline = [
        {"$match": {"_id": oid}},
        {"$unwind": "$precios"},
        {"$lookup": {
            "from": "tiendas",
            "localField": "precios.tiendaId",
            "foreignField": "_id",
            "as": "informacionTienda",
        }},
        {"$unwind": "$informacionTienda"},
        {"$project": {
            "_id": 0,
            "tiendaId": {"$toString": "$informacionTienda._id"},
            "nombre": "$informacionTienda.nombre",
            "url_base": "$informacionTienda.url_base",
            "precio": "$precios.precio",
            "moneda": "$precios.moneda",
            "urlProducto": "$precios.urlProducto",
            "fechaActualizacion": "$precios.fechaActualizacion",
        }},
        {"$sort": {"precio": 1}},
    ]
    tiendas = await db.juegos.aggregate(pipeline).to_list(length=100)
    return preparar_json({
        "juegoId": id_juego, "titulo": juego["titulo"],
        "totalTiendas": len(tiendas), "tiendas": tiendas,
    })


@router.post("/{id_juego}/tiendas", status_code=201)
async def agregar_tienda_a_juego(
    id_juego: str,
    datos: TiendaJuegoCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    oid_juego = validar_id(id_juego, "ID de juego")
    oid_tienda = validar_id(datos.tiendaId, "ID de tienda")
    tienda = await db.tiendas.find_one({"_id": oid_tienda})
    if tienda is None:
        raise HTTPException(status_code=404, detail="Tienda no encontrada")
    juego = await db.juegos.find_one({"_id": oid_juego})
    if juego is None:
        raise HTTPException(status_code=404, detail="Juego no encontrado")
    if any(p.get("tiendaId") == oid_tienda for p in juego.get("precios", [])):
        raise HTTPException(status_code=409, detail="Esta tienda ya está asociada al juego")
    if any(p.get("moneda") != "CLP" for p in juego.get("precios", [])):
        raise HTTPException(status_code=409, detail="El juego tiene precios en otra moneda")

    nuevo_precio = {
        "tiendaId": oid_tienda,
        "precio": datos.precio,
        "moneda": "CLP",
        "urlProducto": datos.urlProducto,
        "fechaActualizacion": datetime.now(timezone.utc),
    }
    # Se agrega el precio y se actualiza el mínimo en una sola operación atómica.
    resultado = await db.juegos.update_one(
        {
            "_id": oid_juego,
            "precios.tiendaId": {"$ne": oid_tienda},
            "precios": {"$not": {"$elemMatch": {"moneda": {"$ne": "CLP"}}}},
        },
        [
            {"$set": {"precios": {"$concatArrays": [{"$ifNull": ["$precios", []]}, [nuevo_precio]]}}},
            etapa_minimo(),
        ],
    )
    if resultado.modified_count == 0:
        raise HTTPException(status_code=409, detail="No se pudo asociar la tienda; revisa duplicados o monedas")
    actualizado = await db.juegos.find_one({"_id": oid_juego}, {"precios": 1, "precio_mas_barato": 1})
    return preparar_json({
        "mensaje": "Tienda asociada al juego exitosamente",
        "juegoId": id_juego,
        "tiendaId": datos.tiendaId,
        "nombreTienda": tienda["nombre"],
        "totalTiendas": len(actualizado.get("precios", [])),
        "precio_mas_barato": actualizado.get("precio_mas_barato"),
    })


@router.delete("/{id_juego}/tiendas/{tienda_id}")
async def eliminar_tienda_de_juego(
    id_juego: str,
    tienda_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    usuario_actual: dict = Depends(get_current_user),
):
    oid_juego = validar_id(id_juego, "ID de juego")
    oid_tienda = validar_id(tienda_id, "ID de tienda")
    juego = await db.juegos.find_one({"_id": oid_juego})
    if juego is None:
        raise HTTPException(status_code=404, detail="Juego no encontrado")
    if not any(p.get("tiendaId") == oid_tienda for p in juego.get("precios", [])):
        raise HTTPException(status_code=404, detail="La tienda no está asociada a este juego")

    resultado = await db.juegos.update_one(
        {"_id": oid_juego, "precios.tiendaId": oid_tienda},
        [
            {"$set": {
                "precios": {
                    "$filter": {
                        "input": "$precios", "as": "p",
                        "cond": {"$ne": ["$$p.tiendaId", oid_tienda]},
                    }
                }
            }},
            etapa_minimo(),
        ],
    )
    if resultado.modified_count == 0:
        raise HTTPException(status_code=409, detail="No se pudo actualizar el juego")
    actualizado = await db.juegos.find_one({"_id": oid_juego}, {"precios": 1, "precio_mas_barato": 1})
    return preparar_json({
        "mensaje": "Tienda eliminada del juego exitosamente",
        "juegoId": id_juego,
        "tiendaId": tienda_id,
        "tiendasRestantes": len(actualizado.get("precios", [])),
        "precio_mas_barato": actualizado.get("precio_mas_barato"),
    })


# --- ELIMINACIÓN DE JUEGO ---
@router.delete("/{id_juego}")
async def eliminar_juego(
    id_juego: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    usuario_actual: dict = Depends(get_current_user),
):
    oid = validar_id(id_juego, "ID de juego")
    juego = await db.juegos.find_one({"_id": oid})
    if juego is None:
        raise HTTPException(status_code=404, detail="Juego no encontrado")
    # Las operaciones de limpieza no son transaccionales.
    await db.calificaciones.delete_many({"juegoId": oid})
    await db.usuarios.update_many(
        {"listaDeseados.juegoId": oid},
        {"$pull": {"listaDeseados": {"juegoId": oid}}}
    )
    await db.juegos.delete_one({"_id": oid})
    return {"mensaje": "Juego eliminado exitosamente", "juegoId": id_juego}


class PrecioUpdate(BaseModel):
    precio: float = Field(ge=0)


@router.put("/{id_juego}/tiendas/{tienda_id}")
async def actualizar_precio_tienda(
    id_juego: str,
    tienda_id: str,
    datos: PrecioUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    usuario_actual: dict = Depends(get_current_user),
):
    """Actualiza el precio y recalcula el mínimo en una sola operación."""
    oid_juego = validar_id(id_juego, "ID de juego")
    oid_tienda = validar_id(tienda_id, "ID de tienda")
    juego = await db.juegos.find_one({"_id": oid_juego})
    if juego is None:
        raise HTTPException(status_code=404, detail="Juego no encontrado")
    if not any(p.get("tiendaId") == oid_tienda for p in juego.get("precios", [])):
        raise HTTPException(status_code=404, detail="Tienda no asociada al juego")
    resultado = await db.juegos.update_one(
        {"_id": oid_juego, "precios.tiendaId": oid_tienda},
        [
            {"$set": {"precios": {"$map": {
                "input": "$precios", "as": "p",
                "in": {"$cond": [
                    {"$eq": ["$$p.tiendaId", oid_tienda]},
                    {"$mergeObjects": ["$$p", {
                        "precio": datos.precio,
                        "fechaActualizacion": "$$NOW",
                    }]},
                    "$$p",
                ]},
            }}}},
            etapa_minimo(),
        ],
    )
    if resultado.matched_count == 0:
        raise HTTPException(status_code=409, detail="No fue posible actualizar el precio")
    actualizado = await db.juegos.find_one({"_id": oid_juego}, {"precio_mas_barato": 1})
    return preparar_json({
        "mensaje": "Precio actualizado exitosamente", "juegoId": id_juego,
        "tiendaId": tienda_id, "nuevoPrecio": datos.precio,
        "precio_mas_barato": actualizado.get("precio_mas_barato"),
    })
