from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from typing import List, Optional, Annotated
from datetime import datetime

# --- TIPO PERSONALIZADO PARA MONGODB ---
# Esta línea le enseña a Pydantic a convertir un ObjectId de Mongo a String
PyObjectId = Annotated[str, BeforeValidator(str)]

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
    id_juego: str
    fecha_agregado: datetime = Field(default_factory=datetime.now)

# --- COLECCIONES PRINCIPALES ---

class Juego(BaseModel):
    # Usamos PyObjectId en lugar de str
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    titulo: str
    descripcion: Optional[str] = None
    fecha_lanzamiento: Optional[datetime] = None
    desarrollador: Optional[str] = None
    imagen_portada: Optional[str] = None
    
    generos: List[str] = []
    plataformas: List[str] = []
    
    precio_mas_barato: Optional[float] = None
    tiendas: List[PrecioTienda] = []

    model_config = ConfigDict(populate_by_name=True)

class Usuario(BaseModel):
    # Usamos PyObjectId en lugar de str
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    nombre: str
    correo: str
    contrasena_hash: str
    fecha_registro: datetime = Field(default_factory=datetime.now)
    
    preferencias: Optional[Preferencia] = None
    lista_deseados: List[JuegoDeseado] = []

    model_config = ConfigDict(populate_by_name=True)

class Calificacion(BaseModel):
    # Usamos PyObjectId en lugar de str
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    id_usuario: str
    id_juego: str
    puntaje: int = Field(ge=1, le=5)
    comentario: Optional[str] = None
    fecha: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(populate_by_name=True)