from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List
from datetime import datetime
from pydantic import BaseModel
from app.database import get_db
from app.models import Usuario

class LoginRequest(BaseModel):
    correo: str

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

@router.get("/", response_model=List[Usuario])
async def listar_usuarios(skip: int = 0, limit: int = 100, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Obtiene la lista de todos los usuarios registrados."""
    cursor = db.usuarios.find().skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

@router.get("/{usuario_id}", response_model=Usuario)
async def obtener_usuario_por_id(usuario_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Busca un usuario específico por su ID de Mongo."""
    if not ObjectId.is_valid(usuario_id):
        raise HTTPException(status_code=400, detail="Formato de ID inválido")
        
    usuario = await db.usuarios.find_one({"_id": ObjectId(usuario_id)})
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario

@router.post("/", response_model=Usuario)
async def crear_usuario(usuario_in: Usuario, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Crea un nuevo usuario en la base de datos."""
    # Convertimos Pydantic a dict excluyendo el id para que Mongo lo genere seguro
    usuario_dict = usuario_in.model_dump(by_alias=True, exclude={"id"})
    
    resultado = await db.usuarios.insert_one(usuario_dict)
    nuevo_usuario = await db.usuarios.find_one({"_id": resultado.inserted_id})
    return nuevo_usuario

@router.post("/login", response_model=Usuario)
async def login_usuario(credenciales: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Busca un usuario por su correo para iniciar sesión."""
    usuario = await db.usuarios.find_one({"correo": credenciales.correo})
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado con ese correo")
    return usuario

@router.put("/{usuario_id}/deseados/{juego_id}")
async def agregar_a_deseados(usuario_id: str, juego_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Agrega un juego a la lista de deseados usando una actualización atómica ($push)."""
    if not ObjectId.is_valid(usuario_id) or not ObjectId.is_valid(juego_id):
        raise HTTPException(status_code=400, detail="Formato de ID inválido")
    
    # Verificamos que el juego exista
    juego_existe = await db.juegos.find_one({"_id": ObjectId(juego_id)})
    if not juego_existe:
        raise HTTPException(status_code=404, detail="El juego que intentas agregar no existe")
    
    nuevo_deseado = {
        "id_juego": juego_id,
        "fecha_agregado": datetime.now()
    }
    
    # Inyectamos el juego en el arreglo del usuario
    resultado = await db.usuarios.update_one(
        {"_id": ObjectId(usuario_id)},
        {"$push": {"lista_deseados": nuevo_deseado}}
    )
    
    if resultado.modified_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado o el juego ya estaba exactamente igual")
        
    return {"mensaje": "Juego agregado a deseados exitosamente"}

@router.get("/{usuario_id}/recomendaciones")
async def obtener_recomendaciones(usuario_id: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Obtiene una lista de juegos recomendados basados en las preferencias del usuario."""
    
    if not ObjectId.is_valid(usuario_id):
        raise HTTPException(status_code=400, detail="Formato de ID inválido")

    # 1. Buscar al usuario
    usuario = await db.usuarios.find_one({"_id": ObjectId(usuario_id)})
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    # 2. Extraer preferencias
    preferencias = usuario.get("preferencias")
    if not preferencias:
        raise HTTPException(status_code=400, detail="El usuario no tiene preferencias configuradas")

    generos_pref = preferencias.get("generos_preferidos", [])
    precio_min = preferencias.get("precio_min", 0)
    precio_max = preferencias.get("precio_max", 999999)

    # 3. Construir la consulta NoSQL para el motor
    query_recomendaciones = {
        "generos": { "$in": generos_pref },
        "precio_mas_barato": { "$gte": precio_min, "$lte": precio_max }
    }

    # 4. Ejecutar la búsqueda en la colección de juegos
    cursor = db.juegos.find(
        query_recomendaciones, 
        {"_id": 0, "titulo": 1, "generos": 1, "precio_mas_barato": 1}
    )
    juegos_recomendados = await cursor.sort("precio_mas_barato", 1).limit(5).to_list(length=None)

    return {
        "usuario": usuario.get("nombre", "Usuario"),
        "criterios_busqueda": preferencias,
        "recomendaciones": juegos_recomendados
    }