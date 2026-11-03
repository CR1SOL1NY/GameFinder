from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from typing import List, Optional, Annotated
from datetime import datetime, timezone

# --- TIPO PERSONALIZADO PARA MONGODB ---
PyObjectId = Annotated[str, BeforeValidator(str)]

# --- SUBDOCUMENTOS (Embebidos) ---
class PrecioTienda(BaseModel):
    tienda: str
    precio: float
    moneda: str = "CLP"
    urlProducto: str
    fechaActualizacion: Optional[datetime] = None

class PrecioMasBarato(BaseModel):
    precio: float
    moneda: str = "CLP"
    tienda: str

class Preferencia(BaseModel):
    precioMin: float = 0.0
    precioMax: float = 999999.0
    generos: List[str] = Field(default_factory=list)

# --- COLECCIONES PRINCIPALES ---
class Juego(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    titulo: str
    descripcion: Optional[str] = None
    fechaLanzamiento: Optional[datetime] = None
    desarrollador: Optional[str] = None
    imagenPortada: Optional[str] = None
    generos: List[str] = Field(default_factory=list)
    plataformas: List[str] = Field(default_factory=list)
    precios: List[PrecioTienda] = Field(default_factory=list)
    precio_mas_barato: Optional[PrecioMasBarato] = None
    activo: bool = True
    model_config = ConfigDict(populate_by_name=True)

class Usuario(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    nombre: str
    correo: str
    contrasenaHash: str
    fechaRegistro: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    preferencias: Optional[Preferencia] = None
    listaDeseados: List[PyObjectId] = Field(default_factory=list)
    model_config = ConfigDict(populate_by_name=True)

class Calificacion(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    usuarioId: PyObjectId
    juegoId: Optional[PyObjectId] = None
    puntaje: int = Field(ge=1, le=5)
    comentario: Optional[str] = None
    fecha: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    visible: bool = True
    model_config = ConfigDict(populate_by_name=True)

# Modelo público: nunca devolver hashes de contraseña al cliente.
class UsuarioPublic(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    nombre: str
    correo: str
    fechaRegistro: datetime
    preferencias: Optional[Preferencia] = None
    listaDeseados: List[PyObjectId] = Field(default_factory=list)
    model_config = ConfigDict(populate_by_name=True)
