# Integración del frontend existente de GameFinder

La rama `funcionalidad/integracion-frontend` incorpora el frontend existente en el repositorio `CR1SOL1NY/GameFinder`. El diseño, las vistas, componentes, servicios de React y recursos públicos se conservan del estado `64326ce25eb4a201d8117f6195e7f7d6d66bad2b` de `xSeVeN-bot/gamefinder`. El archivo `origen-frontend.json` registra los hashes SHA-256 de esos archivos para comprobar que no fueron rediseñados.

La base del repositorio del equipo es `eda69a2f4697934968605d00372c8c18e6bdec18`. Se inspeccionaron `main`, `Actualizacion_entrega2`, `feature/migracion-mongodb` y `prueba_conexion_bd`: las actualizaciones de la entrega 2 ya están integradas en `main`. Los cinco commits iniciales conservaron íntegros `app/`, `main.py` y `requirements.txt`. La revisión posterior de [permisos del backend](SEGURIDAD_BACKEND.md) modifica deliberadamente la autorización de las rutas originales; `requirements.txt` se conserva.

## Entregas por etapas

Los commits describen la integración de código existente, no un desarrollo desde cero ni una cronología reconstruida.

1. Preparar el entorno del frontend con React, TypeScript y Vite.
2. Integrar componentes, estilos y servicios reutilizables del frontend.
3. Incorporar las páginas y funciones actuales de GameFinder.
4. Conectar el frontend mediante una integración opcional de FastAPI.
5. Verificar la integración y documentar su ejecución y procedencia.

## Estructura

```text
main.py, app/, requirements.txt  Backend del equipo, con permisos corregidos
main_interfaz.py                Entrada opcional para ejecutar ambos contratos
integracion_frontend/           Contrato que consume el frontend existente
frontend/                       React + TypeScript + Vite + Tailwind v4
pruebas_interfaz/               Pruebas con datos sintéticos y BD emulada
scripts/probar_integracion.py   Recorridos React → HTTP → FastAPI
scripts/preparar_indices_interfaz.py  Preparación opcional y explícita de índices
```

## Por qué hay una capa de compatibilidad

El backend del equipo no expone todos los contratos que utiliza el frontend actual: faltaban, entre otros, `/juegos/catalogo`, `/usuarios/me`, logout, edición de perfil y reseñas privadas, y difieren el registro y la sesión. Su registro espera `contrasenaHash`; el frontend envía una contraseña al servidor para que la cifre. Cambiar nombres de rutas no resuelve esas diferencias y no se trasladó el hash al navegador.

`main_interfaz.py` importa la aplicación original y monta el contrato compatible bajo **`/interfaz`**. Este utiliza directamente el mismo `client`, `db` y `get_db` de `app.database`. Es un único proceso FastAPI y la misma base MongoDB, sin Express, sin una segunda conexión de aplicación ni sustitución de los routers originales. Seguir usando `uvicorn main:app` conserva la entrada anterior sin este montaje.

El frontend llama a `/api`. En desarrollo Vite reenvía a `http://127.0.0.1:8000/interfaz`; en producción el proxy configurado deberá utilizar la URL pública real del mismo contrato. Los `.env.example` no contienen secretos.

## Ejecución en VS Code

Requisitos: Python 3.12 y Node.js 24. El backend sigue ubicado en la **raíz del repositorio**.

En la **terminal del BACKEND**, situada en la raíz, crea un entorno separado para no alterar el que usa el equipo:

```powershell
py -3.12 -m venv .venv-interfaz
.\.venv-interfaz\Scripts\python.exe -m pip install -r requirements-interfaz.lock.txt
.\.venv-interfaz\Scripts\python.exe -m uvicorn main_interfaz:app --reload --port 8000
```

Antes de arrancar, utiliza el `.env` local que ya tenga el equipo. Si aún no existe, configura los nombres documentados en `.env.example`: `MONGO_URL` o `MONGODB_URI`, `MONGO_DB_NAME` y `JWT_SECRET_KEY` de al menos 32 caracteres. No sobrescribas un `.env` existente ni compartas sus valores. La documentación original queda en `http://127.0.0.1:8000/docs`; la del contrato del frontend, en `http://127.0.0.1:8000/interfaz/docs`.

En una **terminal nueva del FRONTEND**, desde la raíz:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Abre `http://localhost:5173`. Se usa `npm.cmd` para evitar el bloqueo de `npm.ps1` en PowerShell. Para detener cada servicio presiona Ctrl+C en su terminal.

## Funciones conservadas

Inicio, catálogo, búsqueda/filtros/orden/paginación, ficha con Información y Reseñas y comparador lateral, precios separados por moneda/plataforma, cuentas, perfil, preferencias, deseados, medias estrellas, últimas reseñas, comparaciones recientes y avisos locales de bajadas de precio. Administración conserva el editor de juegos, requisitos, tiendas, plataformas y ofertas; exige una cuenta que ya tenga rol administrativo.

Los precios, juegos, reseñas e imágenes provienen de los datos de la API. No se incorporan el catálogo de 229 juegos, imágenes adicionales, precios falsos, cuentas predeterminadas ni scripts de modificación de tiendas. Las recomendaciones son reglas; el historial de comparaciones y los avisos se conservan por cuenta/navegador, sin afirmar sincronización o avisos con la web cerrada.

## Índices y límites del backend

No hay migraciones ni creación de índices durante el arranque de esta integración. El equipo debe provisionar las restricciones de unicidad de correos/reseñas y revisar las necesidades de consultas y sesiones antes de habilitar escrituras concurrentes en producción. La expiración de JWT sí se verifica aunque no exista el TTL de limpieza.

La herramienta opcional se consulta desde la **terminal del BACKEND**, sin escribir:

```powershell
.\.venv-interfaz\Scripts\python.exe -m scripts.preparar_indices_interfaz
```

Si el equipo decide aplicar esa preparación a su base, la misma herramienta admite `--aplicar`. Esa opción **sí crea índices** y debe ejecutarse como una operación de base de datos deliberada, con respaldo y revisión del equipo. Esta herramienta no se ejecutó sobre la base actual de Atlas; las pruebas del paso 2 sí prepararon índices en su base exclusiva y retiraron sus colecciones al finalizar. No elimina datos ni reemplaza índices incompatibles; un conflicto requiere revisión.

Las rutas heredadas ahora aplican la [política de autorización documentada](SEGURIDAD_BACKEND.md): titularidad, roles administrativos y sesiones revocables compartidas. Los tokens antiguos sin `jti` requieren iniciar sesión nuevamente. La [preparación de la prueba con Atlas](PRUEBAS_MONGODB_ATLAS.md) ya está disponible y se verificó con MongoDB real local. La verificación automatizada posterior contra Atlas se completó desde Windows: 154 pruebas del backend y diez recorridos del frontend aprobados en su base exclusiva de pruebas, con limpieza terminada. La revisión de la pull request, la comprobación visual y la preparación de producción siguen pendientes. No se desplegó la aplicación.

## Verificaciones

En la **terminal del FRONTEND**, dentro de `frontend`:

```powershell
npm.cmd test
npm.cmd run build
```

En la **terminal del BACKEND**, desde la raíz:

```powershell
.\.venv-interfaz\Scripts\python.exe -m pip install -r requirements-pruebas-interfaz.lock.txt
.\.venv-interfaz\Scripts\python.exe -m pytest pruebas_interfaz -q
.\.venv-interfaz\Scripts\python.exe scripts\probar_integracion.py
```

Se ejecutaron localmente **81 pruebas DOM del frontend, 83 pruebas iniciales de la API integrada y su montaje, 10 flujos React → HTTP → FastAPI y la compilación TypeScript/Vite**. La base usada en esas comprobaciones iniciales fue emulada y descartable. La revisión posterior añade la [suite con MongoDB real](PRUEBAS_MONGODB_ATLAS.md). El montaje comprueba que el cliente MongoDB sea compartido y que las rutas originales y el nuevo prefijo coexistan. En esa comprobación inicial no se probó Atlas. Posteriormente el usuario ejecutó las pruebas automatizadas contra Atlas desde Windows y compartió los resultados aprobados; consulta el registro del paso 2. No se certifica todavía el aspecto final en un motor de navegador a distintas resoluciones.

También se inició Vite realmente en una prueba HTTP aislada: sirvió el HTML y TypeScript, reenvió `/api/juegos/catalogo` a `/interfaz/juegos/catalogo` y recibió 401 al consultar un perfil sin sesión. Esto comprueba el proxy de desarrollo; no sustituye una prueba visual en navegador.

La configuración de GitHub Actions repite las comprobaciones al subir la rama y en pull requests que afecten al frontend o a cualquiera de las APIs. La revisión de permisos añade 45 pruebas aisladas de las rutas originales; consulta el alcance y los límites en [SEGURIDAD_BACKEND.md](SEGURIDAD_BACKEND.md).

## Publicación futura

`frontend/vercel.json` es una plantilla: su destino `gamefinder-api.example.com` debe sustituirse por la URL pública real del backend más `/interfaz`. Antes de publicar, configura HTTPS, cookies seguras, los orígenes autorizados y verifica el conjunto con una base Atlas separada de pruebas. Los comandos de ejecución local y el proxy de Vite no publican el proyecto.
