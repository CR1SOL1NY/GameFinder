"""Entradas validadas. Los nombres existentes de MongoDB se conservan."""
from typing import Annotated
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator, model_validator

Texto = Annotated[str, Field(min_length=1, max_length=100)]
Puntaje = Annotated[float, Field(ge=0.5, le=5, multiple_of=0.5, strict=True, allow_inf_nan=False)]

class Preferencias(BaseModel):
    precioMin: float = Field(default=0, ge=0, le=1_000_000_000, allow_inf_nan=False)
    precioMax: float = Field(default=999999, ge=0, le=1_000_000_000, allow_inf_nan=False)
    generos: list[Texto] = Field(default_factory=list, max_length=50)
    plataformas: list[Texto] = Field(default_factory=list, max_length=50)

    @model_validator(mode='after')
    def presupuesto(self):
        if self.precioMin > self.precioMax:
            raise ValueError('El presupuesto mínimo no puede superar al máximo')
        return self

class LoginRequest(BaseModel):
    correo: EmailStr
    contrasena: str = Field(min_length=1, max_length=256)

    @field_validator('correo', mode='before')
    @classmethod
    def normalizar_correo(cls, v):
        return v.strip().lower() if isinstance(v, str) else v

class UsuarioCreate(LoginRequest):
    nombre: str = Field(min_length=2, max_length=80)
    contrasena: str = Field(min_length=8, max_length=72)
    preferencias: Preferencias | None = None

    @field_validator('nombre', mode='before')
    @classmethod
    def nombre_valido(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator('contrasena')
    @classmethod
    def password_bytes(cls, v):
        if len(v.encode('utf-8')) > 72:
            raise ValueError('La contraseña admite hasta 72 bytes UTF-8')
        return v

class PerfilUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    nombre: str = Field(min_length=2, max_length=80)
    preferencias: Preferencias

    @field_validator('nombre', mode='before')
    @classmethod
    def trim_nombre(cls, v):
        return v.strip() if isinstance(v, str) else v

class CalificacionCreate(BaseModel):
    # Se acepta usuarioId por compatibilidad, pero siempre se contrasta con la sesión.
    usuarioId: str | None = None
    juegoId: str
    puntaje: Puntaje
    comentario: str = Field(default='', max_length=2000)

class CalificacionJuegoCreate(BaseModel):
    usuarioId: str | None = None
    puntaje: Puntaje
    comentario: str = Field(default='', max_length=2000)

class CalificacionUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    puntaje: Puntaje | None = None
    comentario: str | None = Field(default=None, max_length=2000)

class OfertaCreate(BaseModel):
    tiendaId: str
    precio: float = Field(ge=0, allow_inf_nan=False)
    moneda: str = Field(default='CLP', pattern=r'^[A-Z]{3}$')
    urlProducto: str | None = Field(default=None, max_length=2000)
    plataforma: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator('urlProducto')
    @classmethod
    def enlace(cls, v):
        from urllib.parse import urlparse
        if v and (urlparse(v).scheme not in ('https', 'http') or not urlparse(v).hostname or urlparse(v).username):
            raise ValueError('El enlace debe ser una URL HTTP o HTTPS sin credenciales')
        return v

class GrupoRequisitosWrite(BaseModel):
    """Solo textos verificados; no calcula requisitos ni completa otro grupo."""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    sistemaOperativo: str | None = Field(default=None, max_length=500)
    procesador: str | None = Field(default=None, max_length=500)
    memoria: str | None = Field(default=None, max_length=500)
    graficos: str | None = Field(default=None, max_length=500)
    almacenamiento: str | None = Field(default=None, max_length=500)
    notas: str | None = Field(default=None, max_length=2000)

    @field_validator('*', mode='before')
    @classmethod
    def vacios_nulos(cls, valor):
        return None if isinstance(valor, str) and not valor.strip() else valor

    @model_validator(mode='after')
    def grupo_no_vacio(self):
        if not any(self.model_dump().values()):
            raise ValueError('Indica al menos un requisito o elimina el grupo vacío')
        return self


class RequisitosSistemaWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    plataforma: str = Field(min_length=1, max_length=100)
    minimos: GrupoRequisitosWrite | None = None
    recomendados: GrupoRequisitosWrite | None = None

    @model_validator(mode='after')
    def requisitos_no_vacios(self):
        if self.minimos is None and self.recomendados is None:
            raise ValueError('Indica requisitos mínimos o recomendados, o elimina el bloque')
        return self


class JuegoWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    titulo: str = Field(min_length=1, max_length=200)
    descripcion: str | None = Field(default=None, max_length=20000)
    descripcionCorta: str | None = Field(default=None, max_length=600)
    caracteristicas: list[Annotated[str, Field(min_length=1, max_length=300)]] = Field(default_factory=list, max_length=30)
    requisitosSistema: RequisitosSistemaWrite | None = None
    desarrollador: str | None = Field(default=None, max_length=200)
    fechaLanzamiento: datetime | None = None
    imagenPortada: str | None = Field(default=None, max_length=2000)
    generos: list[Texto] = Field(default_factory=list, max_length=50)
    plataformas: list[Texto] = Field(default_factory=list, max_length=50)
    activo: bool = True

    @field_validator('caracteristicas')
    @classmethod
    def caracteristicas_unicas(cls, valores):
        vistos = set()
        unicos = []
        for valor in valores:
            clave = ' '.join(valor.casefold().split())
            if clave not in vistos:
                vistos.add(clave)
                unicos.append(valor)
        return unicos

    @field_validator('imagenPortada')
    @classmethod
    def imagen(cls, v):
        return OfertaCreate.enlace(v)

class TiendaWrite(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    nombre: str = Field(min_length=1, max_length=100)
    url_base: str | None = Field(default=None, max_length=2000)
    plataformas: list[Texto] | None = Field(default=None, min_length=1, max_length=50)

    @field_validator('plataformas')
    @classmethod
    def plataformas_unicas(cls, valores):
        if valores is None:
            return None
        vistos = set()
        resultado = []
        for valor in valores:
            clave = valor.casefold()
            if clave not in vistos:
                vistos.add(clave)
                resultado.append(valor)
        return resultado

    @field_validator('url_base')
    @classmethod
    def enlace_tienda(cls, v):
        return OfertaCreate.enlace(v)

class OfertaPlataformaCreate(OfertaCreate):
    """Contrato nuevo: cada precio debe declarar su plataforma real."""
    plataforma: str = Field(min_length=1, max_length=100)

class OfertaUpdate(BaseModel):
    precio: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    tiendaId: str | None = None
    moneda: str | None = Field(default=None, pattern=r'^[A-Z]{3}$')
    urlProducto: str | None = Field(default=None, max_length=2000)
    plataforma: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator('urlProducto')
    @classmethod
    def enlace(cls, v):
        return OfertaCreate.enlace(v)

    @model_validator(mode='after')
    def cambios_validos(self):
        if not self.model_fields_set - {'tiendaId'}:
            raise ValueError('Indica al menos un campo de la oferta para actualizar')
        for name in ('precio', 'moneda'):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f'{name} no puede ser nulo')
        return self

class OfertaPorIdUpdate(OfertaUpdate):
    model_config = ConfigDict(extra='forbid')

    @model_validator(mode='after')
    def tienda_inmutable(self):
        if 'tiendaId' in self.model_fields_set:
            raise ValueError('La tienda de una oferta no se puede cambiar; crea otra oferta')
        return self
