"""Conexión asíncrona de FastAPI con la base de datos GameFinder."""
import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL") or os.getenv("MONGODB_URI")
if not MONGO_URL:
    raise RuntimeError(
        "Falta MONGO_URL o MONGODB_URI. Configura una de ellas en tu archivo .env."
    )

# La colección de trabajo está dentro de la BD 'GameFinder' (respetar mayúsculas).
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "GameFinder")
client = AsyncIOMotorClient(MONGO_URL)
db = client[MONGO_DB_NAME]


def get_db():
    """Dependencia utilizada por los routers existentes."""
    return db