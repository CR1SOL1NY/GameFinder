"""Explicaciones seguras: nunca devolver el mensaje original del driver."""
from pymongo.errors import ConfigurationError, ServerSelectionTimeoutError


def explicar_error_mongo(error, etapa):
    codigo = getattr(error, 'code', None)
    codigo = codigo if isinstance(codigo, int) else None
    # Atlas también puede responder 8000 para credenciales rechazadas. La cadena
    # se inspecciona localmente y nunca se devuelve: puede contener datos privados.
    autenticacion_atlas = codigo == 8000 and any(
        texto in str(error).lower() for texto in ('authentication failed', 'bad auth')
    )
    if codigo == 18 or autenticacion_atlas:
        causa = ('Autenticación rechazada. Revisa el usuario de base de datos, '
                 'su contraseña y authSource en la URI de Atlas.')
    elif codigo == 13:
        causa = ('Permisos insuficientes. El usuario de MongoDB necesita acceso '
                 'de lectura/escritura y creación de índices en la base configurada.')
    elif codigo in (85, 86):
        causa = ('Conflicto con un índice existente. Compara sus campos, nombre '
                 'y opciones; no elimines índices ni datos automáticamente.')
    elif codigo == 11000:
        causa = ('Hay datos duplicados que impiden crear un índice único. '
                 'Ejecuta la auditoría de solo lectura antes de decidir cambios.')
    elif isinstance(error, ServerSelectionTimeoutError):
        causa = ('No se pudo alcanzar MongoDB. Revisa la red, DNS, TLS y la IP '
                 'autorizada en Atlas.')
    elif isinstance(error, ConfigurationError):
        causa = 'Revisa el formato de la URI y la configuración de MongoDB.'
    else:
        causa = ('MongoDB rechazó la operación. Ejecuta diagnostico_mongo.py '
                 'y revisa el código de error sin compartir la URI.')
    referencia = f'código {codigo}' if codigo is not None else type(error).__name__
    return f'MongoDB [{etapa}; {referencia}]: {causa}'
