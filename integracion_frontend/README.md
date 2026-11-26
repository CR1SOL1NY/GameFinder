# Compatibilidad del frontend

Esta carpeta adapta el contrato que utiliza el frontend existente de GameFinder, reutilizado de `xSeVeN-bot/gamefinder` en el estado `64326ce25eb4a201d8117f6195e7f7d6d66bad2b`.

El repositorio del equipo tiene rutas y mecanismos de autenticación distintos. `main_interfaz.py` monta este contrato en `/interfaz`, conservando los routers del equipo. La revisión posterior de permisos hace que `app/security.py` reutilice este mismo validador de sesiones. La conexión y la dependencia `get_db` se reutilizan directamente de `app.database`: un solo servidor FastAPI y el mismo cliente MongoDB del equipo, sin Express ni otra base de datos.

Incluye catálogo con filtros/paginación, cuentas con hash en servidor y sesiones HttpOnly, perfil, deseados, medias estrellas, recomendaciones por reglas y administración con permisos. Lee los documentos existentes y conserva los nombres de campos que ya utiliza MongoDB. Los campos opcionales ausentes no se inventan.

No arranca migraciones ni prepara índices automáticamente. `scripts/preparar_indices_interfaz.py` permite revisar y ejecutar por separado esa preparación si el equipo la aprueba. Las restricciones de unicidad de correos/reseñas deben estar provisionadas antes de habilitar escrituras concurrentes en producción. La expiración JWT no depende de la limpieza TTL de sesiones.

La revisión posterior aplica titularidad y permisos administrativos también en las rutas originales; consulta [la política y sus pruebas](../docs/SEGURIDAD_BACKEND.md). Los JWT anteriores sin `jti` requieren iniciar sesión nuevamente. La [verificación automatizada con Atlas separado](../docs/PRUEBAS_MONGODB_ATLAS.md) se completó desde Windows: 154 pruebas del backend y diez recorridos del frontend aprobados, con datos sintéticos y limpieza terminada. La revisión de la pull request, la comprobación visual y la preparación de producción siguen pendientes. El frontend utiliza exclusivamente el contrato de `/interfaz`.

No se copiaron credenciales, juegos de demostración, imágenes adicionales, scripts de modificación de tiendas ni el catálogo de 229 juegos. Los datos sintéticos existen únicamente en las pruebas aisladas.
