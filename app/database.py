import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# Ahora buscaremos una variable exclusiva para Mongo
MONGO_URL = os.getenv("MONGO_URL")

# Crear el cliente asíncrono
client = AsyncIOMotorClient(MONGO_URL)

# Definir la base de datos (puedes cambiar el nombre)
db = client["gamefinder_db"]

# Nueva dependencia: retorna directamente el objeto de base de datos
def get_db():
    return db