"""Modelos Pydantic para la estructura actual de GameFinder en MongoDB Atlas."""
from datetime import datetime, timezone
from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

# Los ObjectId de MongoDB se exponen como cadenas en las respuestas de FastAPI.
PyObjectId = Annotated[str, BeforeValidator(str)]


class MongoModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


# --- SUBDOCUMENTOS ---
class PrecioTienda(MongoModel):
    tiendaId: PyObjectId
    precio: float = Field(ge=0)
    moneda: str = "CLP"
    urlProducto: Optional[str] = None
    fechaActualizacion: Optional[datetime] = None


class PrecioMasBarato(MongoModel):
    precio: float = Field(ge=0)
    moneda: str = "CLP"
    tiendaId: PyObjectId


class Preferencia(MongoModel):
    precioMin: float = 0
    precioMax: float = 999999
    generos: list[str] = Field(default_factory=list)


class JuegoDeseado(MongoModel):
    juegoId: PyObjectId
    fechaAgregado: datetime


# --- COLECCIONES ---
class Juego(MongoModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    titulo: str
    descripcion: Optional[str] = None
    fechaLanzamiento: Optional[datetime] = None
    desarrollador: Optional[str] = None
    imagenPortada: Optional[str] = None
    generos: list[str] = Field(default_factory=list)
    plataformas: list[str] = Field(default_factory=list)
    precios: list[PrecioTienda] = Field(default_factory=list)
    precio_mas_barato: Optional[PrecioMasBarato] = None
    activo: bool = True


class Tienda(MongoModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    nombre: str
    url_base: Optional[str] = None


class Usuario(MongoModel):
    """Modelo interno; NO usarlo como response_model público por el hash."""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    nombre: str
    correo: str
    contrasenaHash: str
    fechaRegistro: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    preferencias: Optional[Preferencia] = None
    listaDeseados: list[JuegoDeseado] = Field(default_factory=list)


class UsuarioPublic(MongoModel):
    """Modelo de respuesta sin contrasenaHash."""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    nombre: str
    correo: str
    fechaRegistro: datetime
    preferencias: Optional[Preferencia] = None
    listaDeseados: list[JuegoDeseado] = Field(default_factory=list)


class Calificacion(MongoModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    usuarioId: PyObjectId
    juegoId: PyObjectId
    puntaje: int = Field(ge=1, le=5)
    comentario: Optional[str] = None
    fecha: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    visible: bool = True