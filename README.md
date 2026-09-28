# GameFinder

GameFinder es una plataforma web de búsqueda, comparación de precios y recomendación personalizada de videojuegos. Esta aplicación centraliza en una sola vista la ficha de cada juego y sus precios vigentes en múltiples tiendas digitales asociadas, resolviendo la dispersión de información en el mercado.  

##  Características principales

* **Comparación de precios centralizada:** El sistema muestra los precios vigentes en tiendas como Steam, Epic Games Store, PlayStation Store, Xbox Store y Nintendo eShop. Los precios de estas fuentes externas se actualizan mediante un proceso automatizado al menos una vez al día.
* **Búsqueda estructurada:** El sistema permite a cualquier usuario buscar juegos por nombre, así como aplicar filtros por género y plataforma.
* **Motor de recomendaciones:** Genera recomendaciones personalizadas de juegos calculando un puntaje de afinidad. Este cálculo se alimenta del historial de calificaciones del usuario y de sus preferencias explícitas, las cuales incluyen géneros favoritos, plataformas disponibles y rango de precio.
* **Sistema de comunidad y reseñas:** Los usuarios registrados pueden otorgar una calificación de 1 a 5 estrellas y redactar una reseña. La plataforma concentra estas evaluaciones para mostrar una calificación promedio de cada juego. Los usuarios también pueden editar o eliminar sus propias calificaciones.
* **Lista de deseados (Wishlist) y notificaciones:** Los usuarios pueden agregar y quitar juegos de una lista de deseados. El sistema notifica de forma automática al usuario cuando existe una baja de precio en alguno de los juegos guardados en esta lista.
* **Panel de administración:** Incluye herramientas para que un administrador pueda crear, editar, deshabilitar y eliminar juegos del catálogo. Además, permite gestionar las tiendas, actualizar precios manualmente y moderar, ocultar o eliminar reseñas que infrinjan las normas de la comunidad.

##  Arquitectura y Diseño

* **Rendimiento:** El sistema asegura tiempos de respuesta menores a 1 segundo para búsquedas y detalles de juegos bajo condiciones normales.
* **Mantenibilidad:** El código del proyecto se organiza en capas (presentación, lógica de negocio y acceso a datos) para facilitar su mantenimiento y evolución.
* **Compatibilidad:** La interfaz es completamente *responsive*, asegurando un correcto funcionamiento en escritorio, tablet y móvil a través de navegadores modernos como Chrome, Firefox y Edge.
* **Seguridad:** Las contraseñas se almacenan utilizando un algoritmo de hash con salt (ej. bcrypt) y las comunicaciones viajan cifradas mediante HTTPS.
