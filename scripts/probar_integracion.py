"""Ejecuta React → FastAPI → MongoDB de prueba y cierra el servidor al terminar.
Usa MongoDB emulado salvo que TEST_MONGODB_URI indique un MongoDB local.
No abre un navegador, no inicia Vite y no carga credenciales de Atlas.
"""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

root=Path(__file__).resolve().parent.parent
venv=root/'.venv-interfaz'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
python=str(venv) if venv.exists() else sys.executable
npm='npm.cmd' if os.name=='nt' else 'npm'

with socket.socket() as check:
    try:
        check.bind(('127.0.0.1',8017))
    except OSError:
        raise SystemExit('El puerto 8017 está ocupado. Cierra el servidor de pruebas anterior antes de continuar.')

with tempfile.TemporaryFile(mode='w+') as log:
    server=subprocess.Popen([python,'-m','uvicorn','pruebas_interfaz.servidor_pruebas:app','--host','127.0.0.1','--port','8017','--no-access-log'],cwd=root,env={**os.environ,'GAMEFINDER_TEST_SERVER':'1'},stdout=log,stderr=subprocess.STDOUT)
    try:
        ready=False
        for _ in range(100):
            if server.poll() is not None:
                break
            try:
                with urlopen('http://127.0.0.1:8017/openapi.json',timeout=.3) as response:
                    ready=response.status==200
                if ready:
                    break
            except OSError:
                time.sleep(.1)
        if not ready:
            log.seek(0)
            print(log.read())
            raise SystemExit('No fue posible iniciar la API de pruebas.')
        result=subprocess.run([npm,'run','test:integration'],cwd=root/'frontend')
        raise SystemExit(result.returncode)
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()
