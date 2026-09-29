from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud

# Creamos un "router" para agrupar todas las URLs que tengan que ver con juegos
router = APIRouter(prefix="/juegos", tags=["Juegos"])

@router.get("/")
def listar_juegos(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.obtener_juegos(db, skip=skip, limit=limit)

@router.get("/buscar")
def buscar_juegos(q: str, db: Session = Depends(get_db)):
    resultados = crud.buscar_juegos_por_titulo(db, query=q)
    if not resultados:
        raise HTTPException(status_code=404, detail="No se encontraron juegos con ese título")
    return resultados

@router.get("/{id_juego}")
def detalle_juego(id_juego: int, db: Session = Depends(get_db)):
    juego = crud.obtener_juego(db, id_juego=id_juego)
    if not juego:
        raise HTTPException(status_code=404, detail="Juego no encontrado")
    return juego