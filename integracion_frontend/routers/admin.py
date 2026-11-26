from fastapi import APIRouter, Depends, Query
from integracion_frontend.database import get_db
from integracion_frontend.security import get_admin
from integracion_frontend.services.common import serializar
router = APIRouter(prefix='/admin', tags=['Administración'], dependencies=[Depends(get_admin)])

@router.get('/registros')
async def registros(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db=Depends(get_db)):
    return serializar(await db.registros.find().sort('fecha', -1).skip(skip).limit(limit).to_list(length=limit))

@router.get('/juegos')
async def juegos_admin(q: str = Query('', max_length=150), skip: int = Query(0, ge=0), limit: int = Query(24, ge=1, le=100), db=Depends(get_db)):
    import re
    from integracion_frontend.services.catalogo import agregar_promedios
    query = {'titulo': {'$regex': re.escape(q.strip()), '$options': 'i'}} if q.strip() else {}
    items = await db.juegos.find(query).sort('titulo', 1).skip(skip).limit(limit).to_list(length=limit)
    return {'items': await agregar_promedios(db, items), 'total': await db.juegos.count_documents(query), 'skip': skip, 'limit': limit}

@router.get('/juegos/{juego_id}')
async def juego_admin(juego_id: str, db=Depends(get_db)):
    from fastapi import HTTPException
    from integracion_frontend.services.common import validar_id
    from integracion_frontend.services.catalogo import agregar_promedios
    game = await db.juegos.find_one({'_id': validar_id(juego_id)})
    if not game:
        raise HTTPException(404, 'Juego no encontrado')
    return (await agregar_promedios(db, [game]))[0]
