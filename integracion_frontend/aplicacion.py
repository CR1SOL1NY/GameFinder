"""Contrato del frontend integrado bajo /interfaz; no sustituye los routers del equipo."""
import logging
import uuid
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import PyMongoError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from integracion_frontend import config
from integracion_frontend.database import comprobar_mongo, crear_indices, db, client
from integracion_frontend.limiter import limiter
from integracion_frontend.security import origen_permitido
from integracion_frontend.services.diagnostico import explicar_error_mongo
from integracion_frontend.routers import juegos, usuarios, tiendas, calificaciones, admin

logger = logging.getLogger('gamefinder')

app = FastAPI(title='API GameFinder', version='2.0.0', description='Catálogo, precios, cuentas y reseñas. Cookie HttpOnly o Bearer; escrituras con cookie requieren Origin autorizado.')
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

@app.middleware('http')
async def seguridad(request: Request, call_next):
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and request.headers.get('origin') and not origen_permitido(request):
        return JSONResponse(status_code=403, content={'detail': 'Origen de solicitud no autorizado'})
    try:
        response = await call_next(request)
    except Exception as error:
        response = await error_interno(request, error)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Cache-Control'] = 'no-store' if request.url.path.removeprefix(request.scope.get('root_path', '')).startswith('/usuarios') else 'no-cache'
    return response

@app.exception_handler(PyMongoError)
async def error_database(request: Request, error):
    error_id = uuid.uuid4().hex[:12]
    logger.error('MongoDB error=%s referencia=%s', type(error).__name__, error_id)
    return JSONResponse(status_code=503, content={'detail': 'No pudimos acceder a la base de datos. Intenta nuevamente.', 'referencia': error_id})

@app.exception_handler(Exception)
async def error_interno(request: Request, error):
    error_id = uuid.uuid4().hex[:12]
    logger.error('API error=%s referencia=%s', type(error).__name__, error_id)
    return JSONResponse(status_code=500, content={'detail': 'Ocurrió un error inesperado. Intenta nuevamente.', 'referencia': error_id})

for router in (juegos.router, usuarios.router, tiendas.router, calificaciones.router, admin.router):
    app.include_router(router)

@app.get('/')
def read_root():
    return {'mensaje': 'La API de GameFinder está ejecutándose', 'docs': '/docs', 'salud_db': '/health/db'}

@app.get('/health/db', tags=['Diagnóstico'])
async def salud_db():
    try:
        await comprobar_mongo()
    except (PyMongoError, HTTPException):
        raise HTTPException(503, 'MongoDB no disponible; revisa la configuración del servidor')
    return {'api': 'ok', 'mongodb': 'conectado'}

app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_credentials=True, allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'], allow_headers=['Content-Type', 'Authorization'])
