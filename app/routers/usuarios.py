from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List
from pydantic import BaseModel
from app.database import get_db
from app.models import Usuario, UsuarioPublic
import bcrypt
from datetime import datetime, timezone


class LoginRequest(BaseModel):
    correo: str
    contrasena: str

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

@router.get("/", response_model=List[UsuarioPublic])
async def listar_usuarios(skip: int = 0, limit: int = 100, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Obtiene la lista de todos los usuarios registrados."""
    cursor = db.usuarios.find().skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

@router.get("/{usuario_id}", response_model=UsuarioPublic)
async def obtener_usuario_por_id(usuario_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Busca un usuario específico por su ID de Mongo."""
    if not ObjectId.is_valid(usuario_id):
        raise HTTPException(status_code=400, detail="Formato de ID inválido")
    usuario = await db.usuarios.find_one({"_id": ObjectId(usuario_id)})
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario

@router.post("/", response_model=UsuarioPublic)
async def crear_usuario(usuario_in: Usuario, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Crea un usuario. contrasenaHash debe contener un hash bcrypt válido."""
    usuario_dict = usuario_in.model_dump(by_alias=True, exclude={"id"})
    if not usuario_dict["contrasenaHash"].startswith(("$2a$", "$2b$", "$2y$")):
        raise HTTPException(status_code=400, detail="contrasenaHash debe contener un hash bcrypt válido")
    if any(not ObjectId.is_valid(i) for i in usuario_in.listaDeseados):
        raise HTTPException(status_code=400, detail="ID inválido en listaDeseados")
    usuario_dict["listaDeseados"] = [ObjectId(i) for i in usuario_in.listaDeseados]
    resultado = await db.usuarios.insert_one(usuario_dict)
    return await db.usuarios.find_one({"_id": resultado.inserted_id})

@router.post("/login", response_model=UsuarioPublic)
async def login_usuario(credenciales: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Comprueba el hash bcrypt de la contraseña de un usuario."""
    usuario = await db.usuarios.find_one({"correo": credenciales.correo})
    if not usuario:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    try:
        valido = bcrypt.checkpw(
            credenciales.contrasena.encode("utf-8"),
            usuario["contrasenaHash"].encode("utf-8")
        )
    except (ValueError, TypeError, KeyError):
        valido = False
    if not valido:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    return usuario

@router.put("/{usuario_id}/deseados/{juego_id}")
async def agregar_a_deseados(usuario_id: str, juego_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Agrega un juego a listaDeseados sin duplicarlo."""
    if not ObjectId.is_valid(usuario_id) or not ObjectId.is_valid(juego_id):
        raise HTTPException(status_code=400, detail="Formato de ID inválido")
    if not await db.juegos.find_one({"_id": ObjectId(juego_id)}):
        raise HTTPException(status_code=404, detail="El juego que intentas agregar no existe")
    resultado = await db.usuarios.update_one(
        {"_id": ObjectId(usuario_id)},
        {"$addToSet": {"listaDeseados": ObjectId(juego_id)}}
    )
    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"mensaje": "Juego agregado a deseados exitosamente"}

@router.get("/{usuario_id}/recomendaciones")
async def obtener_recomendaciones(usuario_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Obtiene recomendaciones según las preferencias del usuario."""
    if not ObjectId.is_valid(usuario_id):
        raise HTTPException(status_code=400, detail="Formato de ID inválido")
    usuario = await db.usuarios.find_one({"_id": ObjectId(usuario_id)})
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    preferencias = usuario.get("preferencias")
    if not preferencias:
        raise HTTPException(status_code=400, detail="El usuario no tiene preferencias configuradas")

    generos_pref = preferencias.get("generos", [])
    precio_min = preferencias.get("precioMin", 0)
    precio_max = preferencias.get("precioMax", 999999)
    query_recomendaciones = {
        "generos": {"$in": generos_pref},
        "precio_mas_barato.precio": {"$gte": precio_min, "$lte": precio_max}
    }
    cursor = db.juegos.find(query_recomendaciones, {
        "_id": 0, "titulo": 1, "generos": 1, "precio_mas_barato": 1
    })
    juegos_recomendados = await cursor.sort("precio_mas_barato.precio", 1).limit(5).to_list(length=5)
    return {
        "usuario": usuario.get("nombre", "Usuario"),
        "criterios_busqueda": preferencias,
        "recomendaciones": juegos_recomendados
    }

@router.delete("/{usuario_id}/deseados/{juego_id}")
async def eliminar_de_deseados(
    usuario_id: str,
    juego_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Elimina un juego de la lista de deseados de un usuario."""

    # 1. Validar los ObjectId
    if not ObjectId.is_valid(usuario_id) or not ObjectId.is_valid(juego_id):
        raise HTTPException(
            status_code=400,
            detail="Formato de ID inválido"
        )

    # 2. Comprobar que el usuario exista
    usuario = await db.usuarios.find_one({
        "_id": ObjectId(usuario_id)
    })

    if not usuario:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado"
        )

    # 3. Eliminar el juego de la lista de deseados
    resultado = await db.usuarios.update_one(
        {"_id": ObjectId(usuario_id)},
        {
            "$pull": {
                "listaDeseados": ObjectId(juego_id)
            }
        }
    )

    # 4. Comprobar si se eliminó
    if resultado.modified_count == 0:
        raise HTTPException(
            status_code=404,
            detail="El juego no está en la lista de deseados"
        )

    # 5. Respuesta
    return {
        "mensaje": "Juego eliminado de la lista de deseados exitosamente",
        "usuarioId": usuario_id,
        "juegoId": juego_id
    }
    
@router.delete("/{usuario_id}")
async def eliminar_usuario(
    usuario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Elimina un usuario y sus calificaciones."""

    # 1. Validar ObjectId
    if not ObjectId.is_valid(usuario_id):
        raise HTTPException(
            status_code=400,
            detail="Formato de ID inválido"
        )

    usuario_oid = ObjectId(usuario_id)

    # 2. Verificar existencia
    usuario = await db.usuarios.find_one({
        "_id": usuario_oid
    })

    if not usuario:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado"
        )

    # 3. Eliminar calificaciones del usuario
    await db.calificaciones.delete_many({
        "usuarioId": usuario_oid
    })

    # 4. Eliminar usuario
    await db.usuarios.delete_one({
        "_id": usuario_oid
    })

    return {
        "mensaje": "Usuario eliminado exitosamente",
        "usuarioId": usuario_id
    }
    
@router.put("/{usuario_id}/deseados/{juego_id}")
async def agregar_a_deseados(
    usuario_id: str,
    juego_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if not ObjectId.is_valid(usuario_id) or not ObjectId.is_valid(juego_id):
        raise HTTPException(status_code=400, detail="ID inválido")

    usuario_oid = ObjectId(usuario_id)
    juego_oid = ObjectId(juego_id)

    if not await db.usuarios.find_one({"_id": usuario_oid}):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if not await db.juegos.find_one({"_id": juego_oid}):
        raise HTTPException(status_code=404, detail="Juego no encontrado")

    resultado = await db.usuarios.update_one(
        {
            "_id": usuario_oid,
            "listaDeseados.juegoId": {"$ne": juego_oid}
        },
        {
            "$push": {
                "listaDeseados": {
                    "juegoId": juego_oid,
                    "fechaAgregado": datetime.now(timezone.utc)
                }
            }
        }
    )

    if resultado.modified_count == 0:
        raise HTTPException(
            status_code=409,
            detail="El juego ya está en la lista de deseados"
        )

    return {"mensaje": "Juego agregado a deseados exitosamente"}

@router.delete("/{usuario_id}/deseados/{juego_id}")
async def eliminar_de_deseados(
    usuario_id: str,
    juego_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if not ObjectId.is_valid(usuario_id) or not ObjectId.is_valid(juego_id):
        raise HTTPException(status_code=400, detail="ID inválido")

    usuario_oid = ObjectId(usuario_id)
    juego_oid = ObjectId(juego_id)

    resultado = await db.usuarios.update_one(
        {"_id": usuario_oid},
        {
            "$pull": {
                "listaDeseados": {"juegoId": juego_oid}
            }
        }
    )

    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if resultado.modified_count == 0:
        raise HTTPException(
            status_code=404,
            detail="El juego no está en la lista de deseados"
        )

    return {"mensaje": "Juego eliminado de deseados exitosamente"}

@router.get("/{usuario_id}/deseados")
async def obtener_lista_deseados(
    usuario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    if not ObjectId.is_valid(usuario_id):
        raise HTTPException(status_code=400, detail="ID inválido")

    usuario_oid = ObjectId(usuario_id)

    usuario = await db.usuarios.find_one({"_id": usuario_oid})

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    pipeline = [
        {"$match": {"_id": usuario_oid}},
        {"$unwind": "$listaDeseados"},
        {
            "$lookup": {
                "from": "juegos",
                "localField": "listaDeseados.juegoId",
                "foreignField": "_id",
                "as": "juego"
            }
        },
        {"$unwind": "$juego"},
        {
            "$project": {
                "_id": 0,
                "juegoId": {"$toString": "$juego._id"},
                "titulo": "$juego.titulo",
                "fechaAgregado": "$listaDeseados.fechaAgregado"
            }
        },
        {"$sort": {"fechaAgregado": -1}}
    ]

    deseados = await db.usuarios.aggregate(pipeline).to_list(length=100)

    return {
        "usuarioId": usuario_id,
        "nombre": usuario["nombre"],
        "totalDeseados": len(deseados),
        "listaDeseados": deseados
    }