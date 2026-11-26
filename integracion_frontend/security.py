"""JWT revocables con cookie HttpOnly; se mantiene compatibilidad con Bearer."""
import secrets
from datetime import datetime, timedelta, timezone
import jwt
from bson import ObjectId
from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPBearer, APIKeyCookie
from integracion_frontend import config
from integracion_frontend.database import get_db


bearer_scheme = HTTPBearer(auto_error=False)
cookie_scheme = APIKeyCookie(name=config.COOKIE_NAME, auto_error=False)

def origen_permitido(request):
    origin = request.headers.get('origin')
    return origin in config.CORS_ORIGINS or origin == str(request.base_url).rstrip('/')

def clave():
    if len(config.JWT_SECRET_KEY) < 32:
        raise HTTPException(503, 'La autenticación requiere configurar JWT_SECRET_KEY en el servidor')
    return config.JWT_SECRET_KEY


def crear_access_token(usuario_id: str, session_id: str):
    ahora = datetime.now(timezone.utc)
    return jwt.encode({'sub': usuario_id, 'jti': session_id, 'iat': ahora, 'exp': ahora + timedelta(minutes=config.TOKEN_MINUTES)}, clave(), algorithm='HS256')


async def nueva_sesion(usuario_id, db):
    session_id = secrets.token_urlsafe(32)
    token = crear_access_token(str(usuario_id), session_id)
    await db.sesiones.insert_one({'_id': session_id, 'usuarioId': ObjectId(usuario_id), 'expira': datetime.now(timezone.utc) + timedelta(minutes=config.TOKEN_MINUTES)})
    return token


async def get_current_user(request: Request, db=Depends(get_db), credentials=Security(bearer_scheme), session_cookie=Security(cookie_scheme)):
    auth = request.headers.get('authorization', '')
    bearer = auth.lower().startswith('bearer ')
    token = auth[7:] if bearer else request.cookies.get(config.COOKIE_NAME)
    error = HTTPException(401, 'Tu sesión expiró o no es válida. Inicia sesión nuevamente.', headers={'WWW-Authenticate': 'Bearer'})
    if not token:
        raise error
    # Las cookies se envían automáticamente: las escrituras requieren un origen autorizado.
    if not bearer and request.method not in ('GET', 'HEAD', 'OPTIONS'):
        origin = request.headers.get('origin')
        if not origen_permitido(request):
            raise HTTPException(403, 'Origen de solicitud no autorizado')
    try:
        payload = jwt.decode(token, clave(), algorithms=['HS256'], options={'require': ['sub', 'jti', 'exp', 'iat']})
        if not ObjectId.is_valid(payload['sub']):
            raise error
        session = await db.sesiones.find_one({'_id': payload['jti'], 'usuarioId': ObjectId(payload['sub'])})
        if not session:
            raise error
        user = await db.usuarios.find_one({'_id': ObjectId(payload['sub']), 'activo': {'$ne': False}})
        if not user:
            raise error
    except (jwt.InvalidTokenError, TypeError, KeyError):
        raise error
    user.pop('contrasenaHash', None)
    user['_sessionId'] = payload['jti']
    return user


async def get_admin(user=Depends(get_current_user)):
    if user.get('rol') != 'admin':
        raise HTTPException(403, 'Se requieren permisos de administrador')
    return user


def propietario(usuario_id, actual):
    if str(actual['_id']) != usuario_id:
        raise HTTPException(403, 'No puedes acceder a información de otro usuario')
