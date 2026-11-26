# Publicación de GameFinder: Render y Vercel

FastAPI está publicado en Render y conectado a MongoDB Atlas. React/Vite conserva su configuración para Vercel; completar y verificar esa conexión es el siguiente paso. La preparación original de `infraestructura/preparacion-despliegue` y las correcciones de búsqueda ya están fusionadas en `main`.

El usuario eligió **Render** y confirmó el workspace **GameFinder**, que ya aparece en la conexión autorizada. No utilizar el workspace personal para crear el servicio.

## Backend publicado: 26 de noviembre de 2026

| Dato | Valor verificado |
| --- | --- |
| URL pública | https://gamefinder-api-uo0o.onrender.com |
| Documentación del contrato del frontend | https://gamefinder-api-uo0o.onrender.com/interfaz/docs |
| Servicio | `gamefinder-api-uo0o` (`srv-dc4b2m59el5s73aot390`) |
| Workspace | `GameFinder` |
| Plan y región | `free`, `virginia` |
| Commit desplegado | `7424e1b2f66db4ec770a4643736eab4605253d1c` |
| Despliegue | `dep-dc4b2ml9el5s73aot4u0`, estado `live` confirmado por Render |
| Blueprint | `exs-dc4b0761egvs73frv6d0`, sincronización automática desactivada |
| Comprobación de salud | `/interfaz/health/db` |

El [servicio en Render](https://dashboard.render.com/web/srv-dc4b2m59el5s73aot390) se creó desde el Blueprint de este repositorio con autorización del usuario. Render añadió un sufijo al nombre para evitar colisiones. Los despliegues automáticos del servicio también están desactivados. El estado `paused` del Blueprint se refiere a su sincronización automática; no indica que el servicio esté apagado.

La URI de `gamefinder_app_user` se configuró como variable privada con autorización específica. Render generó la clave JWT. No se guardan secretos en este documento ni en el repositorio.

Se añadieron al acceso de red del proyecto Atlas únicamente los CIDR `74.220.49.0/24` y `74.220.57.0/24`, copiados por el usuario desde **Connect → Outbound** del servicio. Una consulta posterior confirmó nueve entradas: las siete anteriores conservadas y las dos nuevas. No se modificaron documentos, colecciones ni índices durante este despliegue.

Comprobaciones HTTP públicas ejecutadas después de que Render indicara `live`:

| Ruta | Resultado observado |
| --- | --- |
| `/interfaz/health/db` | HTTP 200, `{"api":"ok","mongodb":"conectado"}` |
| `/interfaz/juegos/catalogo?limit=2` | HTTP 200, dos juegos recibidos y total de 20 |
| `/interfaz/tiendas/` | HTTP 200, 11 tiendas |
| `/interfaz/juegos/filtros` | HTTP 200, 14 géneros y 7 plataformas |
| `/interfaz/usuarios/me` sin sesión | HTTP 401 |
| `/interfaz/docs` y `/docs` | HTTP 200 |

Los totales describen la consulta de esa fecha; no son datos de ejemplo ni valores que la interfaz deba fijar. Estas pruebas solo realizaron lecturas: no se probaron registro, edición, reseñas ni listas de deseos contra la base actual. La consulta final de registros de errores de Render devolvió un error 503 de su servicio de logs; por eso no se afirma haber confirmado ausencia de errores en esos registros.

El plan del Blueprint se validó correctamente en Render mediante MCP. La CLI oficial se descargó en un directorio temporal, pero su validación requirió autenticación separada y no se completó desde esa CLI.

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

La regla de `frontend/vercel.json` envía las solicitudes del navegador al backend público de Render.

```json
{"source":"/api/:path*","destination":"https://gamefinder-api-uo0o.onrender.com/interfaz/:path*"}
```

Conservar la regla SPA hacia `/index.html`, el prefijo `/interfaz` y las cabeceras de seguridad. `CORS_ORIGINS` sigue vacío: completar esa variable con el dominio real y confirmado de Vercel antes de probar las sesiones públicas. Revisar cualquier proyecto Vercel existente antes de cambiarle el directorio raíz o sus variables.

## Comprobaciones de la imagen

Con Docker instalado, en la **terminal del BACKEND**, desde la raíz del repositorio:

```powershell
docker build -t gamefinder-backend:verificacion .
py -3.12 scripts/probar_contenedor_backend.py
```

El script crea una red y contenedores con nombres únicos, usa una base MongoDB sintética y publica la API solo en un puerto de loopback elegido por Docker. Comprueba salud, catálogo vacío, rutas privadas, CORS, usuario de proceso, ausencia de credenciales/servidores de prueba y rechazo del arranque sin JWT. Al terminar retira únicamente sus contenedores, volúmenes anónimos y red. No crea servicios externos ni utiliza Atlas.

La primera construcción local necesitó la CA del proxy del entorno, montada como secreto en una copia temporal del Dockerfile, sin desactivar TLS ni incorporar la CA a la imagen. La ejecución conjunta local encontró falta de espacio en el almacenamiento Docker. La comprobación completa posterior aprobó los 16 controles de la imagen con el Dockerfile del repositorio en [GitHub Actions](https://github.com/CR1SOL1NY/GameFinder/actions/runs/45899200374). El despliegue real de Render también completó la construcción de la imagen.

Después de conectar el frontend, todavía será necesario comprobar el sitio público desde un navegador: rutas directas, catálogo, sesión, logout, permisos, formularios y visualización móvil. Las comprobaciones públicas del backend de esta etapa no certifican todavía esos recorridos del frontend en producción.

## Referencias oficiales

- [Configuración de Blueprints de Render](https://render.com/docs/blueprint-spec).
- [FastAPI en Render](https://render.com/docs/deploy-fastapi).
- [Rangos de salida de Render](https://render.com/docs/outbound-ip-addresses).
