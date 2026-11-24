"""Configuración del servidor. Nunca se importa en el frontend."""
import os
from pathlib import Path
from dotenv import load_dotenv

if os.getenv('GAMEFINDER_TEST_MODE') != '1':
    load_dotenv(Path(__file__).resolve().parent.parent / '.env', override=False)
MONGO_URL = os.getenv('MONGO_URL') or os.getenv('MONGODB_URI')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'GameFinder')
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', '')
TOKEN_MINUTES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '60'))
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'true' if ENVIRONMENT == 'production' else 'false').lower() == 'true'
COOKIE_SAMESITE = os.getenv('COOKIE_SAMESITE', 'lax')
COOKIE_NAME = 'gamefinder_session'
CORS_ORIGINS = [x.strip().rstrip('/') for x in os.getenv('CORS_ORIGINS', os.getenv('CLIENT_ORIGIN', 'http://localhost:5173,http://127.0.0.1:5173')).split(',') if x.strip()]
if '*' in CORS_ORIGINS:
    raise RuntimeError('CORS_ORIGINS debe enumerar dominios concretos')
if COOKIE_SAMESITE not in ('lax', 'strict', 'none') or (COOKIE_SAMESITE == 'none' and not COOKIE_SECURE):
    raise RuntimeError('La cookie SameSite=None requiere HTTPS y COOKIE_SECURE=true')
if ENVIRONMENT == 'production' and (len(JWT_SECRET_KEY) < 32 or not COOKIE_SECURE):
    raise RuntimeError('Producción requiere JWT_SECRET_KEY de al menos 32 caracteres y COOKIE_SECURE=true')
