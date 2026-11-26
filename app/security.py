"""Política compartida de autorización para las dos entradas de FastAPI.

La API original mantiene su contrato Bearer, con sesiones revocables iguales
al contrato /interfaz. Los tokens anteriores sin jti requieren iniciar sesión.
"""
from fastapi import HTTPException
from integracion_frontend import config
from integracion_frontend.security import (
    get_current_user, get_admin, nueva_sesion, propietario,
)

if len(config.JWT_SECRET_KEY) < 32:
    raise RuntimeError("Configura JWT_SECRET_KEY en tu archivo .env")


async def crear_access_token(usuario_id, db):
    return await nueva_sesion(usuario_id, db)


def propietario_o_admin(usuario_id, actual):
    if actual.get("rol") != "admin":
        propietario(usuario_id, actual)


def autor_resena(resena, actual):
    if str(resena["usuarioId"]) != str(actual["_id"]):
        raise HTTPException(403, "Solo puedes editar tus propias calificaciones")
