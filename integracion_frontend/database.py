"""La integración reutiliza el cliente y la dependencia del backend del equipo.
No abre otra conexión ni ejecuta índices durante el arranque.
"""
import logging
from fastapi import HTTPException
from pymongo.errors import PyMongoError
from app.database import client, db, get_db
from integracion_frontend.services.diagnostico import explicar_error_mongo
from integracion_frontend.services.indices import asegurar_indice

async def comprobar_mongo():
    if client is None:
        raise HTTPException(503, 'MongoDB no configurado')
    return await client.admin.command('ping')

async def crear_indices(database):
    # Se conservan las restricciones existentes; no se eliminan índices ni datos.
    indices = [
        ('usuarios', 'correo', {'unique': True, 'name': 'correo_unico_ci', 'collation': {'locale': 'en', 'strength': 2}}),
        ('calificaciones', [('usuarioId', 1), ('juegoId', 1)], {'unique': True, 'name': 'usuario_juego_unico'}),
        ('calificaciones', [('juegoId', 1), ('visible', 1), ('fecha', -1)], {}),
        ('sesiones', 'expira', {'expireAfterSeconds': 0}),
        ('registros', 'fecha', {}),
        ('juegos', 'titulo', {}),
        ('juegos', 'generos', {}),
        ('juegos', 'plataformas', {}),
    ]
    for coleccion, campos, opciones in indices:
        try:
            await asegurar_indice(database[coleccion], campos, **opciones)
        except PyMongoError as error:
            contexto = f'índice de {coleccion}: {opciones.get("name", campos)}'
            logging.getLogger('gamefinder').error('%s', explicar_error_mongo(error, contexto))
            raise
