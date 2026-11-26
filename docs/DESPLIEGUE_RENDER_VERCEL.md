# Publicación de GameFinder: Render y Vercel

La configuración prepara FastAPI para Render y conserva React/Vite para Vercel. Se trabaja en `infraestructura/preparacion-despliegue`, basada en `main` después de fusionar la PR #12. No se ha aplicado un despliegue ni ampliado la lista de acceso de Atlas.

El usuario eligió **Render** y confirmó el workspace **GameFinder**, que ya aparece en la conexión autorizada. No utilizar el workspace personal para crear el servicio.

## Archivos preparados

| Archivo | Uso |
| --- | --- |
| `Dockerfile` | Python 3.12, dependencias de producción verificadas, usuario sin privilegios y entrada `main_interfaz:app` |
| `.dockerignore` | Lista de archivos permitidos; excluye credenciales, frontend, pruebas y entornos virtuales |
| `render.yaml` | Plantilla del servicio, comprobación de MongoDB y despliegues automáticos desactivados |
| `.env.production.example` | Nombres de variables sin secretos; no sustituye el `.env` local |
| `scripts/probar_contenedor_backend.py` | Prueba de la imagen con MongoDB descartable, sin utilizar Atlas |
| `.github/workflows/comprobar-produccion.yml` | Construcción y comprobación de la imagen en GitHub Actions |

No se sustituyeron `requirements.txt`, los routers ni los archivos de ejecución del frontend. La imagen instala `requirements-interfaz.lock.txt` y no contiene los servidores de pruebas. `PORT` se recibe del proveedor; no se utiliza `localhost` como dirección pública.

## Antes de aplicar el despliegue

1. Revisar y fusionar la preparación en `main`. La plantilla usa esa rama como fuente; crear el servicio antes de que incluya el Dockerfile no permitirá construirlo.
2. Revisar el plan de Render y obtener autorización para publicarlo. La plantilla selecciona `free` y la región `virginia`; cualquier cambio de plan o región debe revisarse antes de crear el servicio.
3. Utilizar el workspace **GameFinder**. Si ya existe un servicio con el mismo nombre, no adoptarlo ni modificarlo sin revisar su uso.

La plantilla es una configuración para revisar. Aplicar un Blueprint o crear el servicio sí puede iniciar su primer despliegue. `autoDeployTrigger: "off"` desactiva despliegues futuros por nuevos commits; no convierte la creación del servicio en una operación sin publicación.

## Variables privadas del backend

| Variable | Configuración |
| --- | --- |
| `MONGODB_URI` | URI privada de `gamefinder_app_user`, con acceso únicamente a `GameFinder` y `authSource=admin` |
| `MONGO_DB_NAME` | `GameFinder` |
| `JWT_SECRET_KEY` | El Blueprint solicita generación segura en Render; si se configura manualmente, usar al menos 32 caracteres aleatorios |
| `ENVIRONMENT` | `production` |
| `COOKIE_SECURE` | `true`; el acceso público requiere HTTPS |
| `COOKIE_SAMESITE` | `lax`, usando el proxy del mismo origen en Vercel |
| `CORS_ORIGINS` | Lista exacta de orígenes HTTPS autorizados, separados por coma, cuando se conozcan las URLs públicas |

`MONGODB_URI` no se escribe en el YAML: se solicita como valor privado al aplicar la configuración. No publicar `.env`, `.env.pruebas` ni el archivo privado de la cuenta de aplicación. No copiar variables de MongoDB o JWT al frontend.

La lista de CORS comienza vacía. Esto permite comprobar salud del backend sin autorizar escrituras con cookies desde un frontend todavía no configurado. Antes de habilitar las cuentas desde Vercel, agregar su origen HTTPS exacto. Para usar sesiones desde Swagger también debe autorizarse el origen público del backend.

## Conexión Render → Atlas

Render dispone de rangos de salida por región. Una vez creado el servicio autorizado, consultar **Connect → Outbound** y revisar esos CIDR antes de agregarlos a Atlas. Conservar las entradas existentes y evitar abrir el acceso a todas las IP. No basta con que esté autorizada la IP del computador de desarrollo.

La comprobación de disponibilidad usa `/interfaz/health/db`. Debe responder `{"api":"ok","mongodb":"conectado"}`. El saludo de `/` no comprueba MongoDB. Si la comprobación falla, revisar la URI, los permisos del usuario, DNS/TLS y los rangos de red autorizados. El arranque no crea índices ni modifica documentos automáticamente.

La verificación automatizada del paso 2 utilizó una base separada. Las restricciones e integridad de la base actual deben conservarse; no ejecutar herramientas de preparación sobre ella de forma automática durante el despliegue.

## Conectar Vercel después del backend

Configurar el proyecto de Vercel con **Root Directory `frontend`**, framework Vite, instalación `npm ci`, compilación `npm run build` y salida `dist`. El navegador debe continuar usando `VITE_API_URL=/api`.

Cuando se conozca la URL real de Render, sustituir exclusivamente el destino de ejemplo en `frontend/vercel.json`:

```json
{"source":"/api/:path*","destination":"https://DOMINIO-REAL-DEL-BACKEND/interfaz/:path*"}
```

Este valor todavía es un ejemplo, no una URL publicada. Conservar la regla SPA hacia `/index.html`, el prefijo `/interfaz` y las cabeceras de seguridad. Completar `CORS_ORIGINS` con el dominio real de Vercel antes de probar las sesiones públicas. Revisar cualquier proyecto Vercel existente antes de cambiarle el directorio raíz o sus variables.

## Comprobaciones de la imagen

Con Docker instalado, en la **terminal del BACKEND**, desde la raíz del repositorio:

```powershell
docker build -t gamefinder-backend:verificacion .
py -3.12 scripts/probar_contenedor_backend.py
```

El script crea una red y contenedores con nombres únicos, usa una base MongoDB sintética y publica la API solo en un puerto de loopback elegido por Docker. Comprueba salud, catálogo vacío, rutas privadas, CORS, usuario de proceso, ausencia de credenciales/servidores de prueba y rechazo del arranque sin JWT. Al terminar retira únicamente sus contenedores, volúmenes anónimos y red. No crea servicios externos ni utiliza Atlas.

La primera construcción local necesitó la CA del proxy del entorno, montada como secreto en una copia temporal del Dockerfile, sin desactivar TLS ni incorporar la CA a la imagen. La ejecución conjunta local encontró falta de espacio en el almacenamiento Docker; la comprobación completa se ejecutará en GitHub Actions con el Dockerfile del repositorio. No se presenta un intento fallido como una prueba aprobada.

Después de publicar, todavía será necesario comprobar el sitio público desde un navegador: rutas directas, catálogo, sesión, logout, permisos, formularios y visualización móvil. El arranque local y las pruebas de una imagen no constituyen evidencia de un despliegue público.

## Referencias oficiales

- [Configuración de Blueprints de Render](https://render.com/docs/blueprint-spec).
- [FastAPI en Render](https://render.com/docs/deploy-fastapi).
- [Rangos de salida de Render](https://render.com/docs/outbound-ip-addresses).
