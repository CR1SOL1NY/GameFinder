from fastapi import FastAPI
from app.routers import juegos
from app.database import engine, Base
from app import models

# Esta línea crea todas las tablas en Railway si es que no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(title="API GameFinder")

app.include_router(juegos.router)

@app.get("/")
def read_root():
    return {"mensaje": "¡La API de GameFinder está funcionando y conectada a Railway!"}