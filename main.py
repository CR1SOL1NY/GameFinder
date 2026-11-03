
from fastapi import FastAPI

from app.routers import juegos
from app.routers import usuarios
from app.routers import calificaciones
from app.routers import tiendas

app = FastAPI(title="API GameFinder")

# Registramos los routers de la API
app.include_router(juegos.router)
app.include_router(usuarios.router)
app.include_router(calificaciones.router)
app.include_router(tiendas.router)


@app.get("/")
def read_root():
    return {
        "mensaje": "¡La API de GameFinder está funcionando y conectada a MongoDB Atlas!"
    }
