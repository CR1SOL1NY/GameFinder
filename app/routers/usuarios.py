"""Rutas de usuarios. Solo PUT y DELETE exigen JWT; GET y POST son públicos."""
from datetime import datetime, timezone

import bcrypt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_db
from app.security import crear_access_token, get_current_user

from fastapi import Request
from app.limiter import limiter

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


def serializar(valor):
    return jsonable_encoder(valor, custom_encoder={ObjectId: str})


def publico(usuario):
    return serializar({clave: valor for clave, valor in usuario.items() if clave != "contrasenaHash"})


def validar_id(valor):
    if not ObjectId.is_valid(valor):
        raise HTTPException(status_code=400, detail="Formato de ID inválido")
    return ObjectId(valor)


class LoginRequest(BaseModel):
    correo: str
    contrasena: str


class PreferenciasCreate(BaseModel):
    precioMin: float = 0
    precioMax: float = 999999
    generos: list[str] = Field(default_factory=list)


class UsuarioCreate(BaseModel):
    nombre: str
    correo: str
    contrasenaHash: str
    preferencias: PreferenciasCreate | None = None


@router.get("/")
async def listar_usuarios(
    skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    usuarios = await db.usuarios.find().skip(skip).limit(limit).to_list(length=limit)
    return [publico(u) for u in usuarios]


# Importante: las rutas estáticas van antes de /{usuario_id}.

@router.post("/login")
@limiter.limit("5/minute")
async def login_usuario(
    request: Request,
    credenciales: LoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    # Aquí conservas tu código de autenticación JWT
    # 1. Buscar usuario
    usuario = await db.usuarios.find_one({
        "correo": credenciales.correo
    })

    if not usuario:
        raise HTTPException(
            status_code=401,
            detail="Correo o contraseña incorrectos"
        )

    # 2. Verificar contraseña
    try:
        valido = bcrypt.checkpw(
            credenciales.contrasena.encode("utf-8"),
            usuario.get("contrasenaHash", "").encode("utf-8")
        )
    except (ValueError, TypeError):
        valido = False

    if not valido:
        raise HTTPException(
            status_code=401,
            detail="Correo o contraseña incorrectos"
        )

    # 3. Generar token JWT
    token = crear_access_token(
        str(usuario["_id"])
    )

    # 4. Devolver token y datos públicos
    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": str(usuario["_id"]),
            "nombre": usuario["nombre"],
            "correo": usuario["correo"]
        }
    }


@router.post("/", status_code=201)
async def crear_usuario(datos: UsuarioCreate, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Conserva la entrada contrasenaHash que ya usa el proyecto."""
    if not datos.contrasenaHash.startswith(("$2a$", "$2b$", "$2y$")):
        raise HTTPException(status_code=400, detail="contrasenaHash debe ser un hash bcrypt")
    if await db.usuarios.find_one({"correo": datos.correo}):
        raise HTTPException(status_code=409, detail="El correo ya está registrado")
    documento = {
        "nombre": datos.nombre, "correo": datos.correo,
        "contrasenaHash": datos.contrasenaHash,
        "fechaRegistro": datetime.now(timezone.utc),
        "preferencias": datos.preferencias.model_dump() if datos.preferencias else None,
        "listaDeseados": [],
    }
    resultado = await db.usuarios.insert_one(documento)
    return publico(await db.usuarios.find_one({"_id": resultado.inserted_id}))


@router.get("/{usuario_id}")
async def obtener_usuario_por_id(usuario_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    usuario = await db.usuarios.find_one({"_id": validar_id(usuario_id)})
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return publico(usuario)


@router.put("/{usuario_id}/deseados/{juego_id}")
async def agregar_a_deseados(
    usuario_id: str, juego_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    usuario_actual: dict = Depends(get_current_user),
):
    usuario_oid, juego_oid = validar_id(usuario_id), validar_id(juego_id)
    if not await db.usuarios.find_one({"_id": usuario_oid}):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not await db.juegos.find_one({"_id": juego_oid}):
        raise HTTPException(status_code=404, detail="Juego no encontrado")
    resultado = await db.usuarios.update_one(
        {"_id": usuario_oid, "listaDeseados.juegoId": {"$ne": juego_oid}},
        {"$push": {"listaDeseados": {
            "juegoId": juego_oid, "fechaAgregado": datetime.now(timezone.utc),
        }}},
    )
    if resultado.modified_count == 0:
        raise HTTPException(status_code=409, detail="El juego ya está en deseados")
    return {"mensaje": "Juego agregado a deseados exitosamente"}


@router.delete("/{usuario_id}/deseados/{juego_id}")
async def eliminar_de_deseados(
    usuario_id: str, juego_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    usuario_actual: dict = Depends(get_current_user),
):
    usuario_oid, juego_oid = validar_id(usuario_id), validar_id(juego_id)
    resultado = await db.usuarios.update_one(
        {"_id": usuario_oid}, {"$pull": {"listaDeseados": {"juegoId": juego_oid}}},
    )
    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if resultado.modified_count == 0:
        raise HTTPException(status_code=404, detail="El juego no está en deseados")
    return {"mensaje": "Juego eliminado de deseados exitosamente"}


@router.get("/{usuario_id}/deseados")
async def obtener_lista_deseados(usuario_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    oid = validar_id(usuario_id)
    usuario = await db.usuarios.find_one({"_id": oid})
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    pipeline = [
        {"$match": {"_id": oid}},
        {"$unwind": "$listaDeseados"},
        {"$lookup": {
            "from": "juegos", "localField": "listaDeseados.juegoId",
            "foreignField": "_id", "as": "juego",
        }},
        {"$unwind": "$juego"},
        {"$project": {
            "_id": 0, "juegoId": {"$toString": "$juego._id"},
            "titulo": "$juego.titulo", "fechaAgregado": "$listaDeseados.fechaAgregado",
        }},
        {"$sort": {"fechaAgregado": -1}},
    ]
    deseados = await db.usuarios.aggregate(pipeline).to_list(length=100)
    return serializar({
        "usuarioId": usuario_id, "nombre": usuario["nombre"],
        "totalDeseados": len(deseados), "listaDeseados": deseados,
    })


@router.get("/{usuario_id}/recomendaciones")
async def obtener_recomendaciones(usuario_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    usuario = await db.usuarios.find_one({"_id": validar_id(usuario_id)})
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    preferencias = usuario.get("preferencias")
    if not preferencias:
        raise HTTPException(status_code=400, detail="Sin preferencias configuradas")
    query = {
        "generos": {"$in": preferencias.get("generos", [])},
        "precio_mas_barato.precio": {
            "$gte": preferencias.get("precioMin", 0),
            "$lte": preferencias.get("precioMax", 999999),
        },
    }
    juegos = await db.juegos.find(
        query, {"_id": 0, "titulo": 1, "generos": 1, "precio_mas_barato": 1},
    ).sort("precio_mas_barato.precio", 1).limit(5).to_list(length=5)
    return serializar({
        "usuario": usuario["nombre"], "criterios_busqueda": preferencias,
        "recomendaciones": juegos,
    })


@router.delete("/{usuario_id}")
async def eliminar_usuario(
    usuario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    usuario_actual: dict = Depends(get_current_user),
):
    oid = validar_id(usuario_id)
    if not await db.usuarios.find_one({"_id": oid}):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    # Sin transacciones: las eliminaciones son operaciones independientes.
    await db.calificaciones.delete_many({"usuarioId": oid})
    await db.usuarios.delete_one({"_id": oid})
    return {"mensaje": "Usuario eliminado exitosamente", "usuarioId": usuario_id}
