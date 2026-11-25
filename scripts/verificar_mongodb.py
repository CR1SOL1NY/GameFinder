"""Diagnóstico sin escrituras por defecto; --ejecutar prueba una base vacía aislada.

No lee .env, no imprime la URI y nunca utiliza MONGO_URL/MONGODB_URI del producto.
Ejecutar como módulo desde la raíz: python -m scripts.verificar_mongodb
"""
import argparse
import asyncio
import os
from pathlib import Path
import subprocess
import sys

from dotenv import dotenv_values
from pruebas_interfaz.mongodb_real import ConfiguracionInvalida, cliente, reclamar, liberar, validar_configuracion

ROOT = Path(__file__).resolve().parent.parent


async def verificar(args):
    path = Path(args.config)
    values = dotenv_values(path) if path.exists() else {}
    uri = os.getenv('MONGODB_PRUEBAS_URI') or values.get('MONGODB_PRUEBAS_URI', '')
    nombre = os.getenv('MONGODB_PRUEBAS_DB') or values.get('MONGODB_PRUEBAS_DB', '')
    tipo = validar_configuracion(uri, nombre)
    mongo = cliente(uri)
    token = None
    db = mongo[nombre]
    try:
        await mongo.admin.command('ping')
        info = await mongo.server_info()
        version = info.get('versionArray', [])
        if version[:2] < [5, 2]:
            raise ConfiguracionInvalida('Los pipelines originales requieren MongoDB 5.2 o superior.')
        colecciones = await db.list_collection_names()
        print(f'Conexión: correcta ({tipo}); MongoDB {info["version"]}.', flush=True)
        print(f'Base de pruebas: {nombre}; colecciones existentes: {len(colecciones)}.', flush=True)
        if not args.ejecutar:
            print('Diagnóstico terminado sin escrituras. --ejecutar exige una base vacía y ejecuta pruebas con datos sintéticos.')
            return 0
        token = await reclamar(db)
        entorno = {**os.environ, 'MONGODB_PRUEBAS_URI': uri, 'MONGODB_PRUEBAS_DB': nombre,
                   'GAMEFINDER_PRUEBAS_TOKEN': token, 'GAMEFINDER_MONGODB_REAL': '1'}
        entorno.pop('TEST_MONGODB_URI', None)
        print('Base vacía reclamada exclusivamente para esta verificación. Iniciando pruebas reales.', flush=True)
        # Secuencial: el servidor HTTP y pytest nunca comparten la base simultáneamente.
        for command in ([sys.executable, '-m', 'pytest', 'pruebas_interfaz', '-q', '--tb=short', '--no-header'],
                        [sys.executable, 'scripts/probar_integracion.py']):
            result = subprocess.run(command, cwd=ROOT, env=entorno)
            if result.returncode:
                return result.returncode
        return 0
    finally:
        try:
            if token:
                try:
                    await liberar(db, token)
                except Exception:
                    print('La limpieza no terminó. Revisa únicamente la base de pruebas antes de reutilizarla; puede conservar datos sintéticos.', file=sys.stderr)
                    raise
                print('Limpieza terminada: se retiraron las colecciones creadas para esta ejecución; no se eliminó la base.', flush=True)
        finally:
            mongo.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='.env.pruebas', help='Archivo exclusivo de pruebas; nunca .env')
    parser.add_argument('--ejecutar', action='store_true', help='Ejecutar la suite y limpiar sus datos sintéticos en una base vacía')
    args = parser.parse_args()
    if Path(args.config).name == '.env':
        parser.error('No se permite utilizar el .env de la aplicación. Usa .env.pruebas.')
    try:
        code = asyncio.run(verificar(args))
    except ConfiguracionInvalida as error:
        print(str(error), file=sys.stderr)
        code = 1
    except Exception as error:
        # Los mensajes de PyMongo pueden contener hosts/URI. No se imprimen secretos.
        print(f'No se completó la verificación ({type(error).__name__}). Revisa la cuenta de pruebas, permisos, red y TLS; la URI no se muestra.', file=sys.stderr)
        code = 1
    raise SystemExit(code)


if __name__ == '__main__':
    main()
