from sqlalchemy import Column, Integer, String, Text, Date, DateTime, DECIMAL, ForeignKey, Table, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

# --- TABLAS INTERMEDIAS ---

lista_deseados = Table('LISTA_DESEADOS', Base.metadata,
    Column('id_usuario', Integer, ForeignKey('USUARIO.id_usuario', ondelete="CASCADE"), primary_key=True),
    Column('id_juego', Integer, ForeignKey('JUEGO.id_juego', ondelete="CASCADE"), primary_key=True),
    Column('fecha_agregado', DateTime, default=func.now(), nullable=False)
)

juego_genero = Table('JUEGO_GENERO', Base.metadata,
    Column('id_juego', Integer, ForeignKey('JUEGO.id_juego', ondelete="CASCADE"), primary_key=True),
    Column('id_genero', Integer, ForeignKey('GENERO.id_genero', ondelete="CASCADE"), primary_key=True)
)

juego_plataforma = Table('JUEGO_PLATAFORMA', Base.metadata,
    Column('id_juego', Integer, ForeignKey('JUEGO.id_juego', ondelete="CASCADE"), primary_key=True),
    Column('id_plataforma', Integer, ForeignKey('PLATAFORMA.id_plataforma', ondelete="CASCADE"), primary_key=True)
)

pref_genero = Table('PREF_GENERO', Base.metadata,
    Column('id_preferencia', Integer, ForeignKey('PREFERENCIA.id_preferencia', ondelete="CASCADE"), primary_key=True),
    Column('id_genero', Integer, ForeignKey('GENERO.id_genero', ondelete="CASCADE"), primary_key=True)
)

# --- ENTIDADES PRINCIPALES ---

class Usuario(Base):
    __tablename__ = 'USUARIO'
    id_usuario = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    correo = Column(String(150), nullable=False, unique=True)
    contrasena_hash = Column(String(255), nullable=False)
    fecha_registro = Column(DateTime, default=func.now(), nullable=False)

    preferencia = relationship("Preferencia", back_populates="usuario", uselist=False, cascade="all, delete")
    calificaciones = relationship("Calificacion", back_populates="usuario", cascade="all, delete")
    juegos_deseados = relationship("Juego", secondary=lista_deseados, back_populates="usuarios_que_desean")

class Preferencia(Base):
    __tablename__ = 'PREFERENCIA'
    id_preferencia = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey('USUARIO.id_usuario', ondelete="CASCADE"), nullable=False, unique=True)
    precio_min = Column(DECIMAL(10, 2), nullable=False, default=0)
    precio_max = Column(DECIMAL(10, 2), nullable=False)

    usuario = relationship("Usuario", back_populates="preferencia")
    generos_favoritos = relationship("Genero", secondary=pref_genero)

class Genero(Base):
    __tablename__ = 'GENERO'
    id_genero = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(50), nullable=False, unique=True)

class Plataforma(Base):
    __tablename__ = 'PLATAFORMA'
    id_plataforma = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(50), nullable=False, unique=True)

class Juego(Base):
    __tablename__ = 'JUEGO'
    id_juego = Column(Integer, primary_key=True, autoincrement=True)
    titulo = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    fecha_lanzamiento = Column(Date, nullable=True)
    desarrollador = Column(String(100), nullable=True)
    imagen_portada = Column(String(255), nullable=True)

    precios = relationship("PrecioTienda", back_populates="juego", cascade="all, delete")
    calificaciones = relationship("Calificacion", back_populates="juego")
    generos = relationship("Genero", secondary=juego_genero)
    plataformas = relationship("Plataforma", secondary=juego_plataforma)
    usuarios_que_desean = relationship("Usuario", secondary=lista_deseados, back_populates="juegos_deseados")

class Tienda(Base):
    __tablename__ = 'TIENDA'
    id_tienda = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(80), nullable=False, unique=True)
    url_base = Column(String(255), nullable=False)

    precios = relationship("PrecioTienda", back_populates="tienda", cascade="all, delete")

class PrecioTienda(Base):
    __tablename__ = 'PRECIO_TIENDA'
    id_precio = Column(Integer, primary_key=True, autoincrement=True)
    id_juego = Column(Integer, ForeignKey('JUEGO.id_juego', ondelete="CASCADE"), nullable=False)
    id_tienda = Column(Integer, ForeignKey('TIENDA.id_tienda', ondelete="CASCADE"), nullable=False)
    precio = Column(DECIMAL(10, 2), nullable=False)
    moneda = Column(String(3), nullable=False, default='CLP')
    url_producto = Column(String(255), nullable=False)
    fecha_actualizacion = Column(DateTime, nullable=False)

    juego = relationship("Juego", back_populates="precios")
    tienda = relationship("Tienda", back_populates="precios")

class Calificacion(Base):
    __tablename__ = 'CALIFICACION'
    id_calificacion = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey('USUARIO.id_usuario', ondelete="CASCADE"), nullable=False)
    id_juego = Column(Integer, ForeignKey('JUEGO.id_juego', ondelete="RESTRICT"), nullable=False)
    puntaje = Column(Integer, CheckConstraint('puntaje >= 1 AND puntaje <= 5'), nullable=False)
    comentario = Column(Text, nullable=True)
    fecha = Column(DateTime, default=func.now(), nullable=False)

    usuario = relationship("Usuario", back_populates="calificaciones")
    juego = relationship("Juego", back_populates="calificaciones")