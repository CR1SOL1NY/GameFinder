# Paso 1: permisos del backend original

La integración inicial conservó intactos los routers del equipo. Esta revisión posterior corrige su autorización, sin sustituir FastAPI ni cambiar los nombres de los campos de MongoDB. Se aplica tanto al ejecutar `main:app` como `main_interfaz:app`.

## Problemas corregidos

Las rutas originales permitían listar cuentas y consultar perfiles sin iniciar sesión, escribir reseñas atribuidas a otro usuario y modificar deseados, cuentas, reseñas o catálogo sin comprobar titularidad o rol. Además, un token cerrado en `/interfaz` todavía podía validarse con el mecanismo JWT anterior.

## Política aplicada

| Operación en la API original | Acceso requerido |
| --- | --- |
| Consultar catálogo, fichas, tiendas y reseñas visibles | Público |
| Registro e inicio de sesión | Público, con límite de solicitudes |
| `GET /usuarios/` | Administrador |
| `GET /usuarios/{id}` | Titular o administrador; solo campos de perfil permitidos |
| Leer/agregar/quitar deseados y consultar recomendaciones de una cuenta | Titular |
| `DELETE /usuarios/{id}` | Titular; también se revocan sus sesiones |
| Publicar una reseña, por cualquiera de las dos rutas originales | Usuario autenticado; `usuarioId` debe ser el propio |
| Editar una reseña | Autor; un administrador no puede reescribir opiniones ajenas |
| Eliminar una reseña | Autor o administrador para moderación |
| Crear, actualizar o quitar una oferta de un juego | Administrador |
| Eliminar juegos o tiendas | Administrador |
| `POST /usuarios/logout` | Sesión válida; revoca esa sesión |

El rol se consulta desde el usuario guardado en MongoDB en cada solicitud. No se confía en un rol enviado en el cuerpo o en el JWT. El registro original asigna `rol: usuario`; no crea administradores. Las reseñas nuevas siempre son visibles y se rechazan duplicados del mismo usuario/juego; el cliente no controla la moderación. Las reseñas ocultas se excluyen de lecturas y promedios públicos, y los juegos deshabilitados dejan de aparecer en los endpoints públicos originales.

Las respuestas de cuentas y solicitudes autenticadas llevan `Cache-Control: no-store`. Los perfiles utilizan una lista de campos permitidos y nunca devuelven hashes ni identificadores internos de sesión.

## Sesiones y compatibilidad

`app/security.py` reutiliza el validador de `integracion_frontend.security`, que ya usa el frontend. Ambas APIs comparten el cliente MongoDB, la clave, el vencimiento configurado y la colección `sesiones`. El inicio de sesión original conserva su respuesta `access_token`, `token_type` y `usuario`, pero ahora registra una sesión revocable. El nuevo logout admite Bearer o cookie; las escrituras autenticadas con cookie exigen un origen autorizado.

**Después de actualizar, los tokens antiguos sin `jti` requieren iniciar sesión nuevamente.** Un logout en cualquiera de las APIs impide reutilizar ese token en ambas. Un usuario deshabilitado no puede iniciar sesión ni utilizar una sesión anterior. El registro original conserva la entrada histórica `contrasenaHash`; el frontend sigue usando `/interfaz/usuarios/`, que valida la contraseña y genera bcrypt en el servidor. No se traslada el hash al navegador.

No cambian las URLs existentes. Sí cambian los permisos: una operación sin sesión devuelve 401; una operación ajena o administrativa sin el rol necesario devuelve 403. Se conserva el contrato entero de puntuaciones de las rutas originales; `/interfaz` mantiene las medias estrellas del frontend.

## Verificación aislada

`pruebas_interfaz/test_permisos_originales.py` añade 45 pruebas sobre la aplicación real de FastAPI mediante HTTP ASGI y documentos sintéticos. Cubre accesos anónimos, permisos entre cuentas, administradores, ausencia de escrituras ante rechazos, reseñas, promedios, usuarios inactivos, JWT inválidos/expirados, revocación entre APIs y protección del origen con cookies.

En la **terminal del BACKEND**, desde la raíz del repositorio, con el entorno de integración instalado:

```powershell
.\.venv-interfaz\Scripts\python.exe -m pytest pruebas_interfaz/test_permisos_originales.py -q
.\.venv-interfaz\Scripts\python.exe -m pytest pruebas_interfaz -q
.\.venv-interfaz\Scripts\python.exe scripts\probar_integracion.py
```

Resultado local de esta revisión: **128 pruebas de backend y 10 recorridos React → HTTP → FastAPI aprobados**. Los 42 archivos del frontend registrados en el manifiesto conservan sus hashes. Las 81 pruebas DOM y la compilación también se ejecutan en CI; su resultado remoto debe consultarse en GitHub Actions.

Las pruebas usan MongoDB emulado en memoria y no cargan la conexión real de Atlas. El workflow ejecuta también las pruebas y compilación del frontend en Windows y Linux e incluye cambios de `app/` y `main.py` al comprobar pull requests.

## Alcance y paso siguiente

Durante el paso 1 de permisos no se modificaron datos, índices, credenciales ni tiendas de Atlas. No se fusionó `main` ni se publicó la aplicación. El frontend conserva sus archivos y diseño.

El paso 2 incorpora un [ejecutor de pruebas real](PRUEBAS_MONGODB_ATLAS.md), verificado con MongoDB local y con una **base Atlas separada de pruebas** desde Windows. Se aprobaron 154 pruebas de backend y diez recorridos del frontend, con limpieza terminada. Se comprobaron conexión, restricciones de unicidad y pipelines originales de precios que usan `$sortArray` (MongoDB 5.2 o superior). La suite con servidor real ya ejecuta creación, modificación, eliminación y recálculo de esos precios. La suite emulada comprueba que esos endpoints exijan administrador y que un administrador alcance la validación de recursos; no presenta como ejecutados sus pipelines de escritura reales. Las operaciones compatibles de `/interfaz` conservan sus pruebas existentes.

La preparación de índices continúa siendo explícita y opcional con `scripts/preparar_indices_interfaz.py`; no ocurre al arrancar. Los índices únicos deben provisionarse antes de permitir escrituras concurrentes en producción. Un conflicto o un duplicado existente requiere revisión; esta etapa no los elimina.

Se conservan las eliminaciones físicas existentes de cuentas/juegos y su limpieza no transaccional, ahora con autorización. No se ejecutaron en datos reales; las pruebas solo eliminan documentos sintéticos. Respaldos y validación del equipo son necesarios antes de utilizarlas en producción. Esta revisión de permisos no constituye una auditoría exhaustiva de infraestructura ni habilita por sí sola el despliegue.
