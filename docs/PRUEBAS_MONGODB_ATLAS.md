# Paso 2: comprobar MongoDB real y preparar Atlas

Estado: **verificación con MongoDB real local realizada; conexión a Atlas pendiente de configurar**. No se ha accedido a Atlas ni modificado la base `GameFinder`.

## Qué se comprobó aquí

Se inició un servidor MongoDB **8.0.4 real**, enlazado solo a loopback y con almacenamiento temporal nuevo. El comando de verificación ejecutó **154 pruebas de backend y 10 recorridos React → HTTP → FastAPI**, todos aprobados. Los datos fueron sintéticos y se retiraron al terminar.

Esto incluye los pipelines originales de creación, actualización y eliminación de precios que usan `$sortArray`, el cálculo del precio mínimo, la unicidad real de correos sin distinguir mayúsculas, sesiones, reseñas, permisos, el diagnóstico del cliente MongoDB que utiliza FastAPI y la lectura de deseados desde una segunda conexión a MongoDB. No se presentó mongomock como un servidor real.

También se comprobó con ese servidor que el diagnóstico no escriba, que la ejecución rechace una base ocupada sin alterarla y que se rechacen `GameFinder` y `admin` antes de conectarse. GitHub Actions incorpora un trabajo independiente con MongoDB 8.0.4 en un contenedor descartable; los otros trabajos mantienen la emulación en Windows y Linux.

Esto todavía **no verifica** las credenciales de Atlas, su lista de acceso por IP, TLS/DNS de ese servicio, permisos del usuario remoto ni los documentos del catálogo existente. Tampoco es una prueba visual del navegador.

## 1. Preparar un destino exclusivo en Atlas

Puede utilizarse el mismo clúster, con una base nueva y separada llamada **`gamefinder_pruebas`**. Si ese nombre ya contiene colecciones, utiliza otro nombre nuevo como `gamefinder_pruebas_entrega2`; el script no vacía destinos ocupados.

En **Database Access**, crea un usuario exclusivo para pruebas. Configura el privilegio **`readWrite` únicamente sobre esa base**, para todas sus colecciones. No uses el usuario de la aplicación ni el rol que permite escribir en todas las bases. No cambies las credenciales ni los permisos actuales del proyecto.

En **Network Access**, autoriza la IP del equipo que ejecutará las pruebas. Si ejecutas el comando en tu VS Code, utiliza la IP de ese computador. Conserva las entradas que ya necesita el proyecto.

Obtén en **Connect → Drivers → Python** la URI SRV correspondiente a ese usuario. No incluyas `/GameFinder` en la ruta; puede quedar `/` o el nombre exacto de la base de pruebas. Mantén TLS habilitado. No necesitas crear colecciones manualmente: el modo de ejecución las crea dentro del destino exclusivo de pruebas.

## 2. Configurar VS Code

Actualiza tu copia de `funcionalidad/integracion-frontend`, conservando los cambios locales que tengas. En la **terminal del BACKEND**, ubicada en la raíz del repositorio:

```powershell
.\.venv-interfaz\Scripts\python.exe -m pip install -r requirements-pruebas-interfaz.lock.txt
if (-not (Test-Path .env.pruebas)) { Copy-Item .env.pruebas.example .env.pruebas }
```

Abre `.env.pruebas` en VS Code y completa **solo allí**:

```dotenv
MONGODB_PRUEBAS_URI=
MONGODB_PRUEBAS_DB=gamefinder_pruebas
```

En la primera variable coloca la URI privada de la cuenta de pruebas. Si elegiste otro nombre de base, actualiza la segunda variable. `.env.pruebas` está ignorado por Git; el archivo de ejemplo está vacío y sí se versiona. No envíes la URI, contraseña ni el archivo por chat. Nunca coloques estas variables en el frontend.

La herramienta no lee el `.env` del producto ni utiliza `MONGO_URL` o `MONGODB_URI`. Las variables `MONGODB_PRUEBAS_*` del entorno tienen prioridad sobre `.env.pruebas`.

## 3. Comprobar conexión sin escribir

En la **terminal del BACKEND**, desde la raíz:

```powershell
.\.venv-interfaz\Scripts\python.exe -m scripts.verificar_mongodb
```

El comando comprueba configuración, conexión, versión y lectura de colecciones. Por defecto no crea documentos, colecciones ni índices. No muestra la URI. Si falla, revisa el usuario de pruebas, el nombre de base y la IP permitida; no modifiques el `.env` actual para resolverlo.

## 4. Ejecutar las pruebas aisladas

Cuando el diagnóstico sea correcto, en la **misma terminal del BACKEND**:

```powershell
.\.venv-interfaz\Scripts\python.exe -m scripts.verificar_mongodb --ejecutar
```

Este modo reclama una base **vacía** mediante un marcador exclusivo de la ejecución, crea datos/índices sintéticos, ejecuta pytest y luego los recorridos HTTP del frontend. El servidor HTTP de pruebas escucha solo en `127.0.0.1:8017`, separado del backend normal; no hace falta detener la aplicación. Si el puerto está ocupado, se informa sin detener procesos ajenos.

Las dos suites se ejecutan secuencialmente. La preparación y la limpieza comprueban el marcador, el nombre de base y la ausencia de colecciones desconocidas. Solo se retiran las colecciones de esta verificación; no se ejecuta `dropDatabase` en este modo. No apuntes otra aplicación a esta base mientras se ejecutan las pruebas.

Si se interrumpe el proceso de forma forzada o se pierde la conexión durante la limpieza, podrían quedar datos sintéticos en el destino de pruebas. La siguiente ejecución rechazará el destino ocupado. Utiliza un nuevo nombre de pruebas y revisa el anterior antes de limpiarlo manualmente; el script no elimina automáticamente colecciones anteriores.

El resultado esperado es **todas las pruebas de backend aprobadas, 10 recorridos aprobados y limpieza terminada**. Solo entonces podrá registrarse la comprobación real con Atlas. Comparte únicamente el resumen final, sin la configuración privada.

## Archivos y límites

- `.env.pruebas.example`: configuración separada sin credenciales.
- `scripts/verificar_mongodb.py`: diagnóstico y ejecución deliberada.
- `pruebas_interfaz/mongodb_real.py`: restricciones del destino y propiedad de la ejecución.
- `pruebas_interfaz/test_mongodb_real_seguro.py`: pruebas de las restricciones.
- `pruebas_interfaz/test_persistencia_real.py`: garantías de índices y persistencia que requieren servidor real.
- `pruebas_interfaz/test_permisos_originales.py`: añade el recorrido real de precios del contrato original.

La suite habitual `python -m pytest pruebas_interfaz -q` sigue usando emulación y omite las tres comprobaciones que requieren MongoDB real. No se debe intentar habilitar Atlas mediante `TEST_MONGODB_URI`; esa variable conserva su restricción a MongoDB local. Para Atlas utiliza exclusivamente el ejecutor descrito arriba.

No se copian datos del catálogo actual. Estas pruebas verificarán el código contra Atlas con datos sintéticos; revisar la compatibilidad de documentos reales requerirá después una revisión de lectura o una copia anonimizada autorizada. Este paso no fusiona `main` ni despliega el proyecto.
