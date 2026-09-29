import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

# 1. Cargar las variables del archivo .env
load_dotenv()

# 2. Obtener la URL de Railway
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Reparación automática por si olvidaste poner "+pymysql" en el .env
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("mysql://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

# 3. Crear el "motor" (engine) que se comunica con MySQL en Railway
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 4. Crear la fábrica de sesiones para ejecutar consultas
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 5. Crear la clase Base de la cual heredarán todas nuestras tablas
Base = declarative_base()

# Dependencia para obtener la sesión de la BD en nuestros endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()