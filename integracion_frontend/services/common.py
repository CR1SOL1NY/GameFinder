import math
from bson import ObjectId, Decimal128
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder


def validar_id(value: str):
    if not ObjectId.is_valid(value):
        raise HTTPException(400, 'Formato de ID inválido')
    return ObjectId(value)


def serializar(value):
    return jsonable_encoder(value, custom_encoder={ObjectId: str, Decimal128: lambda v: float(v.to_decimal())})


def publico(user):
    keys = ('_id', 'nombre', 'correo', 'fechaRegistro', 'preferencias', 'listaDeseados', 'rol')
    return serializar({k: user[k] for k in keys if k in user})


def minimo_clp(precios):
    validos = [p for p in precios if p.get('moneda') == 'CLP' and isinstance(p.get('precio'), (int, float)) and not isinstance(p['precio'], bool) and math.isfinite(p['precio']) and p['precio'] >= 0]
    if not validos:
        return None
    p = min(validos, key=lambda p: p['precio'])
    return {k: p[k] for k in ('precio', 'moneda', 'tiendaId', 'plataforma') if k in p}
