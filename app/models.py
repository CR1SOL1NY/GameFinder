from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime

# --- SUBDOCUMENTOS (Embebidos) ---

class PrecioTienda(BaseModel):
    nombre_tienda: str
    precio: float
    moneda: str = "CLP"
    url_producto: str
    fecha_actualizacion: datetime = Field(default_factory=datetime.now)

class Preferencia(BaseModel):
    precio_min: float = 0.0
    precio_max: float
    generos_preferidos: List[str] = []

class JuegoDeseado(BaseModel):
    id_juego: str # Se guarda el ObjectId como string en FastAPI
    fecha_agregado: datetime = Field(default_factory=datetime.now)

# --- COLECCIONES PRINCIPALES ---

class Juego(BaseModel):
    # Field(alias="_id") permite mapear el _id de Mongo a "id" en Python
    id: Optional[str] = Field(alias="_id", default=None)
    titulo: str
    descripcion: Optional[str] = None
    fecha_lanzamiento: Optional[datetime] = None
    desarrollador: Optional[str] = None
    imagen_portada: Optional[str] = None
    
    # Arreglos directos (reemplazan a JUEGO_GENERO y JUEGO_PLATAFORMA)
    generos: List[str] = []
    plataformas: List[str] = []
    
    # Campo precalculado y subdocumentos
    precio_mas_barato: Optional[float] = None
    tiendas: List[PrecioTienda] = []

    model_config = ConfigDict(populate_by_name=True)

class Usuario(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    nombre: str
    correo: str
    contrasena_hash: str
    fecha_registro: datetime = Field(default_factory=datetime.now)
    
    # Subdocumentos embebidos (reemplazan a PREFERENCIA y LISTA_DESEADOS)
    preferencias: Optional[Preferencia] = None
    lista_deseados: List[JuegoDeseado] = []

    model_config = ConfigDict(populate_by_name=True)

class Calificacion(BaseModel):
    id: Optional[str] = Field(alias="_id", default=None)
    id_usuario: str
    id_juego: str
    puntaje: int = Field(ge=1, le=5) # Reemplaza el CheckConstraint de SQL
    comentario: Optional[str] = None
    fecha: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(populate_by_name=True)