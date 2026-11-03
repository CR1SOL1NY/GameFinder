
import os
import jwt

from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.database import get_db

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)

if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise RuntimeError(
        "Configura JWT_SECRET_KEY en tu archivo .env"
    )

bearer_scheme = HTTPBearer(auto_error=False)


# GENERAR TOKEN JWT
def crear_access_token(usuario_id: str):
    ahora = datetime.now(timezone.utc)

    datos = {
        "sub": usuario_id,
        "iat": ahora,
        "exp": ahora + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    }

    return jwt.encode(
        datos,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# VALIDAR TOKEN Y OBTENER USUARIO
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Debes iniciar sesión con un token válido",
        headers={"WWW-Authenticate": "Bearer"}
    )

    if credentials is None:
        raise error

    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        usuario_id = payload.get("sub")

        if not isinstance(usuario_id, str) or not ObjectId.is_valid(usuario_id):
            raise error

    except jwt.InvalidTokenError:
        raise error

    usuario = await db.usuarios.find_one({
        "_id": ObjectId(usuario_id)
    })

    if not usuario:
        raise error

    # No devolver el hash de la contraseña
    usuario.pop("contrasenaHash", None)
    usuario["_id"] = str(usuario["_id"])

    return usuario
