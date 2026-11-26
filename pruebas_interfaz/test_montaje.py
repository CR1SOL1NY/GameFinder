"""Pruebas del montaje adicional, conservando la API del equipo y usando BD emulada."""
import httpx
import pytest
from app import database as original
from integracion_frontend import database as compartida
from integracion_frontend.aplicacion import app as interfaz
from main_interfaz import app


def test_cliente_y_dependencia_mongodb_son_los_del_equipo():
    assert compartida.client is original.client
    assert compartida.get_db is original.get_db
    assert any(getattr(route, 'path', None) == '/interfaz' for route in app.routes)


@pytest.mark.asyncio
async def test_rutas_originales_y_catalogo_con_prefijo_coexisten(env):
    _, db, gid, *_ = env
    app.dependency_overrides[original.get_db] = lambda: db
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://testserver',
                                      headers={'Origin': 'http://localhost:5173'}) as c:
            original_store = await c.get('/tiendas/')
            assert original_store.status_code == 200 and len(original_store.json()) == 1
            catalog = await c.get('/interfaz/juegos/catalogo?q=Alfa')
            assert catalog.status_code == 200 and catalog.json()['items'][0]['_id'] == gid
            assert (await c.get('/interfaz/docs')).status_code == 200
            private = await c.get('/interfaz/usuarios/me')
            assert private.status_code == 401
            assert private.headers['cache-control'] == 'no-store'
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_sesion_y_permisos_funcionan_bajo_prefijo(env):
    _, db, gid, *_ = env
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://testserver',
                                  headers={'Origin': 'http://localhost:5173'}) as c:
        created = await c.post('/interfaz/usuarios/', json={
            'nombre': 'Persona de prueba', 'correo': 'montaje@example.com', 'contrasena': 'ClaveSoloPruebas123!'})
        assert created.status_code == 201, created.text
        login = await c.post('/interfaz/usuarios/login', json={'correo': 'montaje@example.com', 'contrasena': 'ClaveSoloPruebas123!'})
        assert login.status_code == 200 and 'HttpOnly' in login.headers['set-cookie']
        user_id = created.json()['_id']
        assert (await c.put(f'/interfaz/usuarios/{user_id}/deseados/{gid}')).status_code == 200
        assert (await c.get('/interfaz/usuarios/me')).json()['_id'] == user_id
        assert (await c.post('/interfaz/tiendas/', json={'nombre': 'Sin permisos'})).status_code == 403
        assert (await c.post('/interfaz/usuarios/logout')).status_code == 200
        assert (await c.get('/interfaz/usuarios/me')).status_code == 401
