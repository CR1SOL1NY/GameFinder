"""Comprueba una imagen local con MongoDB descartable, sin Atlas ni despliegues.

Terminal BACKEND (raíz): python scripts/probar_contenedor_backend.py
Construye antes la imagen gamefinder-backend:verificacion con Docker.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, ProxyHandler
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', default='gamefinder-backend:verificacion')
    parser.add_argument('--docker-host', help='Socket local de Docker, si el entorno lo requiere')
    args = parser.parse_args()
    command = ['docker'] + (['--host=' + args.docker_host] if args.docker_host else [])
    environment = dict(os.environ)
    if args.docker_host:
        for key in ('DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH'):
            environment.pop(key, None)

    def docker(*parts, check=True):
        result = subprocess.run(command + list(parts), env=environment,
                                capture_output=True, text=True)
        if check and result.returncode:
            raise RuntimeError('Docker ' + parts[0] + ': ' + result.stderr.strip())
        return result

    suffix = uuid.uuid4().hex[:12]
    network = 'gf-verificacion-' + suffix
    mongodb = 'gf-mongo-' + suffix
    backend = 'gf-api-' + suffix
    insecure = 'gf-sin-clave-' + suffix
    origin = 'https://frontend-prueba.example.com'
    opener = build_opener(ProxyHandler({}))  # Solo se consultan puertos de loopback.
    checks = 0

    def expect(condition, message):
        nonlocal checks
        if not condition:
            raise RuntimeError(message)
        checks += 1

    try:
        docker('network', 'create', network)
        docker('run', '-d', '--name', mongodb, '--network', network,
               '--network-alias', 'mongodb', 'mongo:8.0.4')
        with tempfile.TemporaryDirectory(prefix='gamefinder-contenedor-') as folder:
            env_file = Path(folder) / 'backend.env'
            env_file.write_text('\n'.join([
                'MONGODB_URI=mongodb://mongodb:27017/',
                'MONGO_DB_NAME=gamefinder_pruebas_imagen',
                'JWT_SECRET_KEY=' + secrets.token_urlsafe(48),
                'CORS_ORIGINS=' + origin,
                'PORT=8187',  # Comprueba que se respete el puerto del proveedor.
            ]) + '\n')
            env_file.chmod(0o600)
            docker('run', '-d', '--name', backend, '--network', network,
                   '--env-file', str(env_file), '-p', '127.0.0.1::8187', args.image)
            binding = docker('port', backend, '8187/tcp').stdout.strip()
            base = 'http://' + binding

            def request(path, method='GET', headers=None):
                try:
                    response = opener.open(Request(base + path, method=method, headers=headers or {}), timeout=5)
                except HTTPError as error:
                    response = error
                with response:
                    return response.status, response.headers, response.read()

            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                try:
                    status, _, content = request('/interfaz/health/db')
                    if status == 200:
                        break
                except (URLError, TimeoutError):
                    pass
                time.sleep(0.25)
            else:
                raise RuntimeError('El contenedor no estuvo listo dentro del plazo de prueba')

            expect(json.loads(content) == {'api': 'ok', 'mongodb': 'conectado'}, 'Falló la conexión con MongoDB descartable')
            expect(request('/interfaz/docs')[0] == 200, 'No se montó el contrato del frontend')
            status, _, content = request('/interfaz/juegos/catalogo')
            expect(status == 200 and json.loads(content)['total'] == 0, 'El catálogo vacío no respondió correctamente')
            status, headers, _ = request('/interfaz/usuarios/me')
            expect(status == 401 and headers['Cache-Control'] == 'no-store', 'La ruta privada quedó desprotegida')
            expect(request('/interfaz/__tests__/reset', method='POST')[0] == 404, 'Se incluyó el servidor de pruebas en producción')
            status, headers, _ = request('/interfaz/usuarios/login', method='OPTIONS', headers={
                'Origin': origin, 'Access-Control-Request-Method': 'POST',
            })
            expect(status == 200 and headers.get('Access-Control-Allow-Origin') == origin
                   and headers.get('Access-Control-Allow-Credentials') == 'true', 'CORS no reconoce el dominio permitido')
            expect(request('/interfaz/usuarios/login', method='OPTIONS', headers={
                'Origin': 'https://otro-dominio.example.com', 'Access-Control-Request-Method': 'POST',
            })[0] == 400, 'CORS permitió un dominio ajeno')
            uid = docker('exec', backend, 'id', '-u').stdout.strip()
            expect(uid == '10001', 'La API se está ejecutando como root')
            result = docker('exec', backend, 'python', '-c',
                            "from pathlib import Path; p=Path('/srv/gamefinder'); "
                            "assert not any(f.name.startswith('.env') for f in p.rglob('*')); "
                            "assert not (p/'pruebas_interfaz').exists(); "
                            "assert not (p/'frontend').exists(); "
                            "assert not Path('/run/secrets/proxy_ca').exists()")
            expect(result.returncode == 0, 'La imagen incluyó archivos privados o de desarrollo')

        rejected = docker('run', '--name', insecure, '--network', network,
                          '-e', 'MONGODB_URI=mongodb://mongodb:27017/', args.image, check=False)
        expect(rejected.returncode != 0 and 'JWT_SECRET_KEY' in rejected.stderr,
               'Producción arrancó sin configurar la clave de sesión')
        print(f'{checks} comprobaciones del contenedor aprobadas. No se utilizó Atlas ni se publicó la aplicación.')
    except Exception:
        logs = docker('logs', '--tail', '30', backend, check=False)
        print(logs.stdout + logs.stderr)
        raise
    finally:
        for name in (insecure, backend, mongodb):
            docker('rm', '-f', '-v', name, check=False)
        docker('network', 'rm', network, check=False)


if __name__ == '__main__':
    main()
