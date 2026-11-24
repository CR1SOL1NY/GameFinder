"""Preparación opcional de índices; nunca se ejecuta al iniciar la interfaz.

Sin --aplicar solo describe la operación. La aplicación sobre Atlas la decide el equipo.
No elimina datos ni reemplaza índices incompatibles.
"""
import argparse
import asyncio


async def aplicar():
    from integracion_frontend.database import comprobar_mongo, crear_indices, get_db
    await comprobar_mongo()
    await crear_indices(get_db())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aplicar', action='store_true')
    args = parser.parse_args()
    if not args.aplicar:
        print('Sin cambios. La operación opcional crea índices de unicidad de correos/reseñas, sesiones y consultas del catálogo.')
        print('El equipo debe revisar la configuración y respaldos antes de ejecutarla con --aplicar.')
        return
    try:
        asyncio.run(aplicar())
    except Exception as error:
        print('No se completó la preparación de índices:', type(error).__name__)
        raise SystemExit(1) from None
    print('Índices verificados. No se eliminaron documentos ni se reemplazaron índices incompatibles.')


if __name__ == '__main__':
    main()
