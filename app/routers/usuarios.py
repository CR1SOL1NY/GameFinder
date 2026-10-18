from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Usuario  # Asegúrate de que la clase en models.py se llame 'Usuario' o ajústala

# Opcional: Si tienes esquemas Pydantic configurados
# from app.schemas import UsuarioCreate, UsuarioResponse 

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"]
)

# Dependencia para obtener la sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/")
def listar_usuarios(db: Session = Depends(get_db)):
    """Obtiene la lista de todos los usuarios registrados."""
    usuarios = db.query(Usuario).all()
    return usuarios

@router.get("/{usuario_id}")
def obtener_usuario_por_id(usuario_id: int, db: Session = Depends(get_db)):
    # Cambiamos Usuario.id por Usuario.id_usuario
    usuario = db.query(Usuario).filter(Usuario.id_usuario == usuario_id).first()
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario

@router.post("/")
def crear_usuario(nombre: str, correo: str, db: Session = Depends(get_db)):
    """Crea un nuevo usuario en la base de datos."""
    # Nota: Ajusta 'nombre' y 'correo' según las columnas exactas de tu tabla en MySQL
    nuevo_usuario = Usuario(nombre=nombre, correo=correo)
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario