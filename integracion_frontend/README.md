# Compatibilidad del frontend

Esta carpeta adapta el contrato que utiliza el frontend existente de GameFinder, reutilizado de `xSeVeN-bot/gamefinder` en el estado `64326ce25eb4a201d8117f6195e7f7d6d66bad2b`.

El repositorio del equipo tiene rutas y mecanismos de autenticación distintos. En vez de sustituir `main.py`, `app/security.py`, sus modelos o sus routers, `main_interfaz.py` monta este contrato en `/interfaz`. La conexión y la dependencia `get_db` se reutilizan directamente de `app.database`: un solo servidor FastAPI y el mismo cliente MongoDB del equipo, sin Express ni otra base de datos.

Incluye catálogo con filtros/paginación, cuentas con hash en servidor y sesiones HttpOnly, perfil, deseados, medias estrellas, recomendaciones por reglas y administración con permisos. Lee los documentos existentes y conserva los nombres de campos que ya utiliza MongoDB. Los campos opcionales ausentes no se inventan.

No arranca migraciones ni prepara índices automáticamente. `scripts/preparar_indices_interfaz.py` permite revisar y ejecutar por separado esa preparación si el equipo la aprueba. Las restricciones de unicidad de correos/reseñas deben estar provisionadas antes de habilitar escrituras concurrentes en producción. La expiración JWT no depende de la limpieza TTL de sesiones.

Las rutas originales del equipo conservan sus contratos y permisos actuales; esta integración no afirma corregir su seguridad global. Deben auditarse antes de publicar el conjunto. El frontend utiliza exclusivamente el contrato de `/interfaz`.

No se copiaron credenciales, juegos de demostración, imágenes adicionales, scripts de modificación de tiendas ni el catálogo de 229 juegos. Los datos sintéticos solo se incorporarán a las pruebas aisladas.
