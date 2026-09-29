from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models

# --- CONSULTAS DE USUARIO ---

# 1. Registrar un nuevo usuario
def crear_usuario(db: Session, nombre: str, correo: str, contrasena_hash: str):
    nuevo_usuario = models.Usuario(nombre=nombre, correo=correo, contrasena_hash=contrasena_hash)
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

# 2. Buscar usuario por correo (Sirve para el Login)
def obtener_usuario_por_correo(db: Session, correo: str):
    return db.query(models.Usuario).filter(models.Usuario.correo == correo).first()


# --- CONSULTAS DE JUEGOS Y BUSCADOR ---

# 3. Listar el catálogo de juegos (con paginación)
def obtener_juegos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Juego).offset(skip).limit(limit).all()

# 4. Obtener el detalle completo de un solo juego por su ID
def obtener_juego(db: Session, id_juego: int):
    return db.query(models.Juego).filter(models.Juego.id_juego == id_juego).first()

# 5. Buscar juegos por título (Para la barra de búsqueda del Frontend)
def buscar_juegos_por_titulo(db: Session, query: str):
    return db.query(models.Juego).filter(models.Juego.titulo.ilike(f"%{query}%")).all()


# --- CONSULTAS DE PRECIOS Y TIENDAS ---

# 6. Obtener todos los precios en diferentes tiendas para un juego específico
def obtener_precios_juego(db: Session, id_juego: int):
    return db.query(models.PrecioTienda).filter(models.PrecioTienda.id_juego == id_juego).all()


# --- CONSULTAS DE LISTA DE DESEADOS (WISHLIST) ---

# 7. Agregar un juego a la lista de deseados de un usuario
def agregar_a_deseados(db: Session, id_usuario: int, id_juego: int):
    usuario = db.query(models.Usuario).filter(models.Usuario.id_usuario == id_usuario).first()
    juego = db.query(models.Juego).filter(models.Juego.id_juego == id_juego).first()
    if usuario and juego:
        usuario.juegos_deseados.append(juego) # SQLAlchemy maneja la tabla intermedia automáticamente
        db.commit()
        return True
    return False

# 8. Ver todos los juegos en la lista de deseados de un usuario
def obtener_deseados_usuario(db: Session, id_usuario: int):
    usuario = db.query(models.Usuario).filter(models.Usuario.id_usuario == id_usuario).first()
    return usuario.juegos_deseados if usuario else []


# --- CONSULTAS DE CALIFICACIONES (RESEÑAS) ---

# 9. Agregar una calificación y comentario a un juego
def agregar_calificacion(db: Session, id_usuario: int, id_juego: int, puntaje: int, comentario: str = ""):
    nueva_calificacion = models.Calificacion(
        id_usuario=id_usuario, 
        id_juego=id_juego, 
        puntaje=puntaje, 
        comentario=comentario
    )
    db.add(nueva_calificacion)
    db.commit()
    db.refresh(nueva_calificacion)
    return nueva_calificacion

# 10. Ver todas las calificaciones de un juego específico
def obtener_calificaciones_juego(db: Session, id_juego: int):
    return db.query(models.Calificacion).filter(models.Calificacion.id_juego == id_juego).all()