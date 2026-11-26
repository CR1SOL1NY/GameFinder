"""Cuentas, sesiones revocables, perfil y listas guardadas en MongoDB."""
import re
from datetime import datetime, timezone
import bcrypt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pymongo.errors import DuplicateKeyError
from starlette.concurrency import run_in_threadpool
from integracion_frontend import config
from integracion_frontend.database import get_db
from integracion_frontend.security import get_current_user, nueva_sesion, propietario, clave
from integracion_frontend.schemas import UsuarioCreate, LoginRequest, PerfilUpdate
from integracion_frontend.services.common import publico, serializar, validar_id
from integracion_frontend.services.catalogo import catalogo
from integracion_frontend.services.perfil import juegos_de_resenas, resumen_calificaciones, precios_deseados
from integracion_frontend.limiter import limiter

router = APIRouter(prefix='/usuarios', tags=['Usuarios'])

@router.get('/')
async def listar_usuarios(db=Depends(get_db), actual=Depends(get_current_user)):
    return [publico(actual)]

@router.post('/', status_code=201)
@limiter.limit('5/minute')
async def crear_usuario(request: Request, datos: UsuarioCreate, db=Depends(get_db)):
    clave()  # Evita crear una cuenta si el servidor no puede iniciar sesiones.
    correo = str(datos.correo).lower()
    if await db.usuarios.find_one({'correo': {'$regex': '^' + re.escape(correo) + '$', '$options': 'i'}}):
        raise HTTPException(409, 'El correo ya está registrado')
    hash_password = await run_in_threadpool(bcrypt.hashpw, datos.contrasena.encode(), bcrypt.gensalt())
    doc = {'nombre': datos.nombre, 'correo': correo, 'contrasenaHash': hash_password.decode(), 'fechaRegistro': datetime.now(timezone.utc), 'preferencias': datos.preferencias.model_dump() if datos.preferencias else None, 'listaDeseados': [], 'rol': 'usuario', 'activo': True}
    try:
        await db.usuarios.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(409, 'El correo ya está registrado')
    return publico(doc)

@router.post('/login')
@limiter.limit('5/minute')
async def login_usuario(request: Request, response: Response, credenciales: LoginRequest, db=Depends(get_db)):
    user = await db.usuarios.find_one({'correo': {'$regex': '^' + re.escape(str(credenciales.correo)) + '$', '$options': 'i'}, 'activo': {'$ne': False}})
    valid = False
    if user:
        try:
            valid = await run_in_threadpool(bcrypt.checkpw, credenciales.contrasena.encode(), user.get('contrasenaHash', '').encode())
        except (ValueError, TypeError):
            pass
    if not valid:
        raise HTTPException(401, 'Correo o contraseña incorrectos')
    token = await nueva_sesion(user['_id'], db)
    response.set_cookie(config.COOKIE_NAME, token, max_age=config.TOKEN_MINUTES * 60, httponly=True, secure=config.COOKIE_SECURE, samesite=config.COOKIE_SAMESITE, path='/')
    return {'access_token': token, 'token_type': 'bearer', 'usuario': {'id': str(user['_id']), 'nombre': user['nombre'], 'correo': user['correo']}}

@router.get('/me')
async def mi_perfil(actual=Depends(get_current_user)):
    return publico(actual)

@router.post('/logout')
async def logout(response: Response, db=Depends(get_db), actual=Depends(get_current_user)):
    await db.sesiones.delete_one({'_id': actual['_sessionId']})
    response.delete_cookie(config.COOKIE_NAME, path='/', httponly=True, secure=config.COOKIE_SECURE, samesite=config.COOKIE_SAMESITE)
    return {'mensaje': 'Sesión cerrada'}

@router.get('/me/calificaciones')
async def mis_calificaciones(skip: int = 0, db=Depends(get_db), actual=Depends(get_current_user)):
    if skip < 0:
        raise HTTPException(422, 'Paginación inválida')
    rows = await db.calificaciones.find({'usuarioId': actual['_id']}).sort([('fecha', -1), ('_id', -1)]).skip(skip).limit(50).to_list(length=50)
    return serializar(await juegos_de_resenas(db, rows))

@router.get('/me/resumen-calificaciones')
async def resumen_mis_calificaciones(db=Depends(get_db), actual=Depends(get_current_user)):
    """Total, promedio de todas las calificaciones propias y las tres más recientes. Solo lectura."""
    return serializar(await resumen_calificaciones(db, actual['_id']))

@router.get('/me/precios-deseados')
async def precios_de_mis_deseados(db=Depends(get_db), actual=Depends(get_current_user)):
    """Ofertas actuales de la lista propia para comprobar bajadas. No guarda avisos ni historial."""
    return serializar(await precios_deseados(db, actual))

@router.get('/{usuario_id}')
async def obtener_usuario_por_id(usuario_id: str, db=Depends(get_db), actual=Depends(get_current_user)):
    propietario(usuario_id, actual)
    return publico(actual)

@router.put('/{usuario_id}')
async def actualizar_perfil(usuario_id: str, datos: PerfilUpdate, db=Depends(get_db), actual=Depends(get_current_user)):
    propietario(usuario_id, actual)
    await db.usuarios.update_one({'_id': validar_id(usuario_id)}, {'$set': datos.model_dump()})
    return publico(await db.usuarios.find_one({'_id': validar_id(usuario_id)}))

@router.get('/{usuario_id}/deseados')
async def obtener_lista_deseados(usuario_id: str, db=Depends(get_db), actual=Depends(get_current_user)):
    propietario(usuario_id, actual)
    desired = actual.get('listaDeseados', [])
    games = await db.juegos.find({'_id': {'$in': [d['juegoId'] for d in desired]}}, {'titulo': 1}).to_list(length=len(desired)) if desired else []
    titles = {str(g['_id']): g.get('titulo') for g in games}
    items = [{**d, 'titulo': titles.get(str(d['juegoId']))} for d in desired]
    return serializar({'usuarioId': usuario_id, 'nombre': actual['nombre'], 'totalDeseados': len(desired), 'listaDeseados': items})

@router.put('/{usuario_id}/deseados/{juego_id}')
async def agregar_a_deseados(usuario_id: str, juego_id: str, db=Depends(get_db), actual=Depends(get_current_user)):
    propietario(usuario_id, actual)
    gid = validar_id(juego_id)
    if not await db.juegos.find_one({'_id': gid, 'activo': {'$ne': False}}):
        raise HTTPException(404, 'Juego no encontrado')
    await db.usuarios.update_one({'_id': validar_id(usuario_id), 'listaDeseados.juegoId': {'$ne': gid}}, {'$push': {'listaDeseados': {'juegoId': gid, 'fechaAgregado': datetime.now(timezone.utc)}}})
    return {'mensaje': 'Juego guardado en tu lista'}

@router.delete('/{usuario_id}/deseados/{juego_id}')
async def eliminar_de_deseados(usuario_id: str, juego_id: str, db=Depends(get_db), actual=Depends(get_current_user)):
    propietario(usuario_id, actual)
    await db.usuarios.update_one({'_id': validar_id(usuario_id)}, {'$pull': {'listaDeseados': {'juegoId': validar_id(juego_id)}}})
    return {'mensaje': 'Juego quitado de tu lista'}

@router.get('/{usuario_id}/recomendaciones')
async def obtener_recomendaciones(usuario_id: str, db=Depends(get_db), actual=Depends(get_current_user)):
    propietario(usuario_id, actual)
    prefs = actual.get('preferencias') or {}
    # Intersección de géneros/plataformas y presupuesto CLP; sin etiquetas de IA.
    page = await catalogo(db, limit=12, genero=prefs.get('generos') or None, plataforma=prefs.get('plataformas') or None, precio_min=prefs.get('precioMin') if prefs else None, precio_max=prefs.get('precioMax') if prefs else None, sort='precio')
    return {'usuario': actual['nombre'], 'criterios_busqueda': prefs, 'recomendaciones': page['items']}

@router.delete('/{usuario_id}')
async def eliminar_usuario(usuario_id: str, db=Depends(get_db), actual=Depends(get_current_user)):
    propietario(usuario_id, actual)
    # Desactivación reversible; no se eliminan datos ni reseñas existentes.
    await db.usuarios.update_one({'_id': validar_id(usuario_id)}, {'$set': {'activo': False}})
    await db.sesiones.delete_many({'usuarioId': validar_id(usuario_id)})
    return {'mensaje': 'Cuenta desactivada'}
