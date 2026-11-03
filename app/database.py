import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# Compatible con el nombre original y con el utilizado en el seed de Atlas.
MONGO_URL = os.getenv("MONGO_URL") or os.getenv("MONGODB_URI")
if not MONGO_URL:
    raise RuntimeError("Falta MONGO_URL o MONGODB_URI. Configúrala en tu archivo .env.")

client = AsyncIOMotorClient(MONGO_URL)
db = client[os.getenv("MONGO_DB_NAME", "GameFinder")]

def get_db():
    return db
