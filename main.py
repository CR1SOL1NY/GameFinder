
from fastapi import FastAPI, Request
from integracion_frontend import config

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


@app.middleware("http")
async def proteger_cache_privada(request: Request, call_next):
    response = await call_next(request)
    if (request.url.path.startswith("/usuarios") or request.headers.get("authorization")
            or request.cookies.get(config.COOKIE_NAME)):
        response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


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
