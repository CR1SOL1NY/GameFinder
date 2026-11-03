
from fastapi import FastAPI

from app.routers import juegos
from app.routers import usuarios
from app.routers import calificaciones
from app.routers import tiendas

from app.limiter import limiter

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware


app = FastAPI(title="API GameFinder")

# Configuración de límites de solicitudes
app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)

app.add_middleware(SlowAPIMiddleware)

# Registrar routers
app.include_router(juegos.router)
app.include_router(usuarios.router)
app.include_router(calificaciones.router)
app.include_router(tiendas.router)


@app.get("/")
def read_root():
    return {
        "mensaje": "¡La API de GameFinder está funcionando y conectada a MongoDB Atlas!"
    }
