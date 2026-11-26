"""Acceso exclusivo a una base vacía de pruebas; nunca se usa el .env del producto."""
import os
import re
import secrets
from urllib.parse import parse_qsl, unquote, urlsplit

from motor.motor_asyncio import AsyncIOMotorClient

COLECCIONES = ('usuarios', 'juegos', 'tiendas', 'calificaciones', 'sesiones', 'registros')
MARCADOR = '_verificacion_gamefinder'


class ConfiguracionInvalida(ValueError):
    """Error de configuración con un mensaje seguro para mostrar."""


def validar_base(nombre):
    if not re.fullmatch(r'gamefinder_pruebas(?:_[a-z0-9]+)?', nombre or ''):
        raise ConfiguracionInvalida('La base debe llamarse gamefinder_pruebas o gamefinder_pruebas_<sufijo>. No se admite GameFinder.')


def validar_configuracion(uri, nombre):
    validar_base(nombre)
    if not uri:
        raise ConfiguracionInvalida('Falta MONGODB_PRUEBAS_URI en .env.pruebas o en el entorno.')
    try:
        parsed = urlsplit(uri)
        host = parsed.hostname or ''
        if ',' in parsed.netloc.rsplit('@', 1)[-1] or (parsed.scheme == 'mongodb+srv' and parsed.port is not None):
            raise ValueError
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError
        local = parsed.scheme == 'mongodb' and host in ('127.0.0.1', 'localhost', '::1')
        atlas = parsed.scheme == 'mongodb+srv' and host.endswith('.mongodb.net')
        if not local and not atlas:
            raise ValueError
        if unquote(parsed.path).strip('/') not in ('', nombre):
            raise ValueError
        for key, value in parse_qsl(parsed.query):
            if (key.lower() in ('tlsinsecure', 'tlsallowinvalidcertificates', 'tlsallowinvalidhostnames') and value.lower() == 'true') or (atlas and key.lower() in ('tls', 'ssl') and value.lower() == 'false'):
                raise ValueError
    except ValueError:
        raise ConfiguracionInvalida('Usa una URI SRV de Atlas con TLS o MongoDB local, sin otra base en la ruta ni opciones TLS inseguras.') from None
    return 'MongoDB local' if local else 'MongoDB Atlas'


def configurar_conexion_aplicacion():
    """Configura el cliente del producto hacia el destino de pruebas, antes de importarlo."""
    os.environ.pop('MONGODB_URI', None)
    if os.getenv('GAMEFINDER_MONGODB_REAL') == '1':
        uri = os.getenv('MONGODB_PRUEBAS_URI', '')
        nombre = os.getenv('MONGODB_PRUEBAS_DB', '')
        validar_configuracion(uri, nombre)
        if not os.getenv('GAMEFINDER_PRUEBAS_TOKEN'):
            raise ConfiguracionInvalida('La aplicación de pruebas requiere una ejecución reclamada por el verificador.')
        os.environ['MONGO_URL'] = uri
        os.environ['MONGO_DB_NAME'] = nombre
    else:
        os.environ['MONGO_URL'] = 'mongodb://127.0.0.1:27017/?directConnection=true'
        os.environ['MONGO_DB_NAME'] = 'gamefinder_tests_sin_conexion'


def cliente(uri):
    return AsyncIOMotorClient(uri, serverSelectionTimeoutMS=10000, connectTimeoutMS=10000)


async def reclamar(db):
    validar_base(db.name)
    if await db.list_collection_names():
        raise ConfiguracionInvalida('La base de pruebas no está vacía. No se modificó; elige una base de pruebas nueva.')
    token = secrets.token_hex(32)
    # _id único: dos verificaciones simultáneas no pueden reclamar la misma base.
    await db[MARCADOR].insert_one({'_id': 'propietario', 'token': token})
    return token


async def comprobar_propietario(db, token):
    validar_base(db.name)
    if not token or not await db[MARCADOR].find_one({'_id': 'propietario', 'token': token}):
        raise RuntimeError('La base no pertenece a esta ejecución de pruebas. Se cancela la escritura.')
    names = set(await db.list_collection_names())
    if names - {*COLECCIONES, MARCADOR}:
        raise RuntimeError('Aparecieron colecciones ajenas a las pruebas. Se cancela la limpieza.')


async def limpiar_colecciones(db, token):
    await comprobar_propietario(db, token)
    for name in COLECCIONES:
        await db.drop_collection(name)


async def liberar(db, token):
    await limpiar_colecciones(db, token)
    await db.drop_collection(MARCADOR)


async def conectar_pruebas():
    uri = os.getenv('MONGODB_PRUEBAS_URI', '')
    nombre = os.getenv('MONGODB_PRUEBAS_DB', '')
    token = os.getenv('GAMEFINDER_PRUEBAS_TOKEN', '')
    validar_configuracion(uri, nombre)
    mongo = cliente(uri)
    try:
        db = mongo[nombre]
        await comprobar_propietario(db, token)
    except BaseException:
        mongo.close()
        raise
    return mongo, db, token
