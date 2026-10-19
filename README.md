# GameFinder

GameFinder es una plataforma web de búsqueda, comparación de precios y recomendación personalizada de videojuegos. Esta aplicación centraliza en una sola vista la ficha de cada juego y sus precios vigentes en múltiples tiendas digitales asociadas, resolviendo la dispersión de información en el mercado.  

## Características principales

* **Comparación de precios centralizada:** El sistema muestra los precios vigentes en tiendas como Steam, Epic Games Store, PlayStation Store, Xbox Store y Nintendo eShop. Los precios de estas fuentes externas se actualizan mediante un proceso automatizado al menos una vez al día.
* **Búsqueda estructurada:** El sistema permite a cualquier usuario buscar juegos por nombre, así como aplicar filtros por género y plataforma.
* **Motor de recomendaciones:** Genera recomendaciones personalizadas de juegos calculando un puntaje de afinidad. Este cálculo se alimenta del historial de calificaciones del usuario y de sus preferencias explícitas, las cuales incluyen géneros favoritos, plataformas disponibles y rango de precio.
* **Sistema de comunidad y reseñas:** Los usuarios registrados pueden otorgar una calificación de 1 a 5 estrellas y redactar una reseña. La plataforma concentra estas evaluaciones para mostrar una calificación promedio de cada juego. Los usuarios también pueden editar o eliminar sus propias calificaciones.
* **Lista de deseados (Wishlist) y notificaciones:** Los usuarios pueden agregar y quitar juegos de una lista de deseados. El sistema notifica de forma automática al usuario cuando existe una baja de precio en alguno de los juegos guardados en esta lista.
* **Panel de administración:** Incluye herramientas para que un administrador pueda crear, editar, deshabilitar y eliminar juegos del catálogo. Además, permite gestionar las tiendas, actualizar precios manualmente y moderar, ocultar o eliminar reseñas que infrinjan las normas de la comunidad.

## Arquitectura y Diseño

* **Rendimiento:** El sistema asegura tiempos de respuesta menores a 1 segundo para búsquedas y detalles de juegos bajo condiciones normales, optimizado gracias a un backend con soporte **100% asíncrono**.
* **Mantenibilidad:** El código del proyecto se organiza por dominios (enrutadores, modelos y bases de datos) para facilitar su evolución. Se eliminaron dependencias monolíticas centralizadas a favor de un diseño modular.
* **Persistencia de Datos (NoSQL):** La base de datos adopta un enfoque orientado a documentos. Para evitar operaciones costosas de cruce de datos (JOINs) y maximizar la velocidad de lectura, atributos complejos como la `lista_deseados` y las `tiendas` se guardan como sub-documentos embebidos.
* **Compatibilidad:** La interfaz es completamente *responsive*, asegurando un correcto funcionamiento en escritorio, tablet y móvil a través de navegadores modernos como Chrome, Firefox y Edge.
* **Seguridad:** Las contraseñas se almacenan utilizando un algoritmo de hash con salt (ej. bcrypt) y las comunicaciones viajan cifradas mediante HTTPS.

## Tecnologías Utilizadas

* **Backend:** Python, FastAPI, Pydantic v2 (para validación y serialización BSON/ObjectId).
* **Base de Datos:** MongoDB (NoSQL) con Motor (Driver asíncrono).
* **Infraestructura:** Despliegue de base de datos y backend en la plataforma en la nube Railway.
* **Control de Versiones:** Git y GitHub.

## Estructura del Backend

El backend ha sido refactorizado, moviendo la lógica de consultas de un archivo global hacia módulos específicos por entidad:
* `main.py`: Punto de entrada de la aplicación y registro de rutas principales, posicionado en la raíz del proyecto.
* `app/models.py`: Modelos de datos estructurados para traducción fluida entre objetos de base de datos (BSON) y respuestas web (JSON).
* `app/routers/juegos.py`: Centraliza las operaciones del catálogo, motor de búsqueda y la gestión de reseñas de la comunidad asociadas al juego.
* `app/routers/usuarios.py`: Gestiona las cuentas de usuario, el inicio de sesión (Login) y las actualizaciones atómicas para agregar o quitar juegos de la Wishlist.

## Instalación y Ejecución Local

1. Clonar el repositorio:
   ```bash
   git clone [POR COMPLETAR - URL del repositorio de GitHub]
   cd gamefinder-backend
