from fastapi import FastAPI
from app.routers import juegos
from app.routers import usuarios

app = FastAPI(title="API GameFinder")

# Incluimos las rutas refactorizadas para MongoDB
app.include_router(juegos.router)
app.include_router(usuarios.router)

@app.get("/")
def read_root():
    return {"mensaje": "¡La API de GameFinder está funcionando y conectada a MongoDB en Railway!"}