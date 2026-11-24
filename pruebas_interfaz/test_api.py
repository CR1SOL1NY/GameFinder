import pytest
from bson import ObjectId
from pruebas_interfaz.conftest import register,login

@pytest.mark.asyncio
async def test_catalog_filters_prices_and_missing(env):
    c,db,gid,gid2,tid=env
    r=await c.get('/juegos/catalogo',params={'q':'Alfa','genero':'RPG','plataforma':'PC','precio_min':10000,'precio_max':20000})
    assert r.status_code==200,r.text
    assert r.json()['total']==1 and r.json()['items'][0]['_id']==gid
    assert (await c.get('/juegos/catalogo',params={'precio_max':100})).json()['total']==0
    assert (await c.get('/juegos/catalogo')).json()['total']==2
    assert (await c.get('/juegos/catalogo',params={'q':'.*'})).json()['total']==0
    assert (await c.get('/juegos/catalogo',params={'limit':0})).status_code==422
    assert (await c.get('/juegos/',params={'skip':-1})).status_code==422
    assert (await c.get('/juegos/no-valido')).status_code==400
    assert (await c.get('/juegos/'+str(ObjectId()))).status_code==404
    assert (await c.get('/juegos/filtros')).json()=={'generos':['Aventura','RPG'],'plataformas':['PC','PS5']}
    offers=(await c.get('/juegos/'+gid+'/tiendas')).json()['tiendas']
    assert {o['moneda'] for o in offers}=={'CLP','USD'}
    assert all(o.get('plataforma') is None for o in offers)

@pytest.mark.asyncio
async def test_pagination_and_order(env):
    c,db,*_=env
    await db.juegos.insert_many([{'titulo':f'ZZ Prueba {n:03}','generos':[],'plataformas':[],'precios':[]} for n in range(110)])
    a=(await c.get('/juegos/catalogo',params={'limit':100})).json()
    b=(await c.get('/juegos/catalogo',params={'limit':100,'skip':100})).json()
    assert a['total']==112 and len(a['items'])==100 and len(b['items'])==12
    assert not {g['_id'] for g in a['items']}&{g['_id'] for g in b['items']}
    assert (await c.get('/juegos/catalogo',params={'orden':'precio'})).json()['items'][0]['titulo']=='Juego de prueba Alfa'

@pytest.mark.asyncio
async def test_register_hash_session_logout(env):
    c,db,*_=env
    u=await register(c)
    assert 'contrasenaHash' not in u and u['rol']=='usuario'
    stored=await db.usuarios.find_one({'_id':ObjectId(u['_id'])})
    assert stored['contrasenaHash'].startswith('$2b$')
    assert (await c.post('/usuarios/',json={'nombre':'Ana','correo':'ANA@EXAMPLE.COM','contrasena':'12345678'})).status_code==409
    assert (await c.post('/usuarios/login',json={'correo':'ana@example.com','contrasena':'mal'})).status_code==401
    session=await login(c)
    cookie=c.cookies.get('gamefinder_session'); assert cookie
    me=await c.get('/usuarios/me');assert me.status_code==200 and me.json()['_id']==u['_id']
    assert 'access_token' not in me.json() and 'contrasenaHash' not in me.text
    out=await c.post('/usuarios/logout');assert out.status_code==200
    assert (await c.get('/usuarios/me')).status_code==401
    assert (await c.get('/usuarios/me',headers={'Authorization':'Bearer '+session['access_token']})).status_code==401

@pytest.mark.asyncio
async def test_private_ownership_and_wishlist_persistence(env):
    c,db,gid,gid2,tid=env
    assert (await c.get('/usuarios/')).status_code==401
    ana=await register(c);await login(c)
    path=f"/usuarios/{ana['_id']}/deseados/{gid}"
    assert (await c.put(path)).status_code==200
    assert (await c.put(path)).status_code==200
    assert len((await c.get(f"/usuarios/{ana['_id']}/deseados")).json()['listaDeseados'])==1
    await c.post('/usuarios/logout');await login(c)
    assert (await c.get('/usuarios/me')).json()['listaDeseados'][0]['juegoId']==gid
    otro=await register(c,'otro@example.com');await login(c,'otro@example.com')
    for method,path2 in [('GET',f"/usuarios/{ana['_id']}"),('GET',f"/usuarios/{ana['_id']}/deseados"),('GET',f"/usuarios/{ana['_id']}/recomendaciones"),('PUT',path),('DELETE',path),('DELETE',f"/usuarios/{ana['_id']}")]:
      assert (await c.request(method,path2)).status_code==403
    await login(c)
    assert (await c.delete(path)).status_code==200
    assert (await c.get('/usuarios/me')).json()['listaDeseados']==[]

@pytest.mark.asyncio
async def test_profile_preferences_and_recommendations(env):
    c,db,gid,*_=env
    u=await register(c);await login(c)
    data={'nombre':'Nuevo Nombre','preferencias':{'generos':['RPG'],'plataformas':['PC'],'precioMin':0,'precioMax':20000}}
    r=await c.put('/usuarios/'+u['_id'],json=data);assert r.status_code==200,r.text
    assert (await c.get('/usuarios/me')).json()['nombre']=='Nuevo Nombre'
    rec=await c.get(f"/usuarios/{u['_id']}/recomendaciones");assert rec.status_code==200,rec.text
    assert rec.json()['recomendaciones'][0]['_id']==gid
    data['preferencias']['precioMin']=30000
    assert (await c.put('/usuarios/'+u['_id'],json=data)).status_code==422

@pytest.mark.asyncio
async def test_reviews_all_routes_require_auth_and_ownership(env):
    c,db,gid,*_=env
    assert (await c.post('/calificaciones/',json={'juegoId':gid,'puntaje':5})).status_code==401
    assert (await c.post(f'/juegos/{gid}/calificaciones',json={'puntaje':5})).status_code==401
    u=await register(c);await login(c)
    assert (await c.post('/calificaciones/',json={'usuarioId':str(ObjectId()),'juegoId':gid,'puntaje':5})).status_code==403
    r=await c.post('/calificaciones/',json={'juegoId':gid,'puntaje':4,'comentario':'Prueba aislada'});assert r.status_code==201,r.text
    rid=r.json()['_id']
    assert (await c.post(f'/juegos/{gid}/calificaciones',json={'puntaje':5})).status_code==409
    assert (await c.put('/calificaciones/'+rid,json={'puntaje':6})).status_code==422
    assert (await c.put('/calificaciones/'+rid,json={'puntaje':5})).status_code==200
    assert (await c.get('/calificaciones/mia/'+gid)).json()['puntaje']==5
    detail=(await c.get('/juegos/'+gid)).json();assert detail['promedioCalificaciones']==5 and detail['totalCalificaciones']==1
    await register(c,'otro@example.com');await login(c,'otro@example.com')
    assert (await c.put('/calificaciones/'+rid,json={'puntaje':1})).status_code==403
    assert (await c.delete('/calificaciones/'+rid)).status_code==403
    await login(c);assert (await c.delete('/calificaciones/'+rid)).status_code==200
    assert (await c.get('/juegos/'+gid)).json()['totalCalificaciones']==0

@pytest.mark.asyncio
async def test_hidden_reviews_excluded(env):
    c,db,gid,*_=env
    await db.calificaciones.insert_one({'juegoId':ObjectId(gid),'usuarioId':ObjectId(),'puntaje':1,'visible':False})
    assert (await c.get('/calificaciones/juego/'+gid)).json()==[]
    assert (await c.get('/juegos/'+gid)).json()['totalCalificaciones']==0

@pytest.mark.asyncio
async def test_admin_and_cors(env):
    c,db,gid,gid2,tid=env
    u=await register(c);session=await login(c)
    assert (await c.delete('/juegos/'+gid)).status_code==403
    assert (await c.post(f'/juegos/{gid}/tiendas',json={'tiendaId':tid,'precio':1})).status_code==403
    assert (await c.get('/admin/registros')).status_code==403
    assert (await c.get('/admin/juegos')).status_code==403
    assert (await c.put(f"/usuarios/{u['_id']}/deseados/{gid}",headers={'Origin':'https://evil.invalid'})).status_code==403
    await db.usuarios.update_one({'_id':ObjectId(u['_id'])},{'$set':{'rol':'admin'}})
    assert (await c.post(f'/juegos/{gid2}/tiendas',json={'tiendaId':tid,'precio':0,'moneda':'CLP','plataforma':'PS5'})).status_code==201
    game=await db.juegos.find_one({'_id':ObjectId(gid2)});assert game['precio_mas_barato']['precio']==0
    assert (await c.post(f'/juegos/{gid2}/tiendas',json={'tiendaId':tid,'precio':-1})).status_code==422
    assert (await c.post(f'/juegos/{gid2}/tiendas',json={'tiendaId':tid,'precio':1,'urlProducto':'javascript:alert(1)'})).status_code==422
    assert (await c.delete('/juegos/'+gid2)).status_code==200
    assert await db.juegos.find_one({'_id':ObjectId(gid2)}) is not None
    assert (await c.get('/juegos/'+gid2)).status_code==404
    admin_game=await c.get('/admin/juegos/'+gid2)
    assert admin_game.status_code==200 and admin_game.json()['activo'] is False
    assert len((await c.get('/admin/juegos')).json()['items'])==2
    assert len((await c.get('/admin/registros')).json())>=2
    pre=await c.options('/usuarios/me',headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'GET'})
    assert pre.headers['access-control-allow-origin']=='http://localhost:5173'

@pytest.mark.asyncio
@pytest.mark.parametrize('data',[{'nombre':'a','correo':'bad','contrasena':'12345678'},{'nombre':'Ana','correo':'ana@example.com','contrasena':'corta'},{'nombre':'   ','correo':'ana@example.com','contrasena':'12345678'}])
async def test_registration_validation(env,data):
    c,*_=env
    assert (await c.post('/usuarios/',json=data)).status_code==422

@pytest.mark.asyncio
async def test_cookie_attributes_csrf_and_expired_token(env):
    import jwt
    from datetime import datetime,timedelta,timezone
    from integracion_frontend import config
    c,db,gid,*_=env
    user=await register(c)
    r=await c.post('/usuarios/login',json={'correo':'ana@example.com','contrasena':'PruebaSegura123!'})
    assert r.status_code==200
    assert 'HttpOnly' in r.headers['set-cookie'] and 'SameSite=lax' in r.headers['set-cookie']
    expired=jwt.encode({'sub':user['_id'],'jti':'prueba','iat':datetime.now(timezone.utc)-timedelta(hours=2),'exp':datetime.now(timezone.utc)-timedelta(hours=1)},config.JWT_SECRET_KEY,algorithm='HS256')
    assert (await c.get('/usuarios/me',headers={'Authorization':'Bearer '+expired})).status_code==401
    assert (await c.get('/usuarios/me',headers={'Authorization':'Bearer '+r.json()['access_token']+'x'})).status_code==401
    c.headers.pop('Origin')
    assert (await c.put(f"/usuarios/{user['_id']}/deseados/{gid}")).status_code==403
    assert (await c.put(f"/usuarios/{user['_id']}/deseados/{gid}",headers={'Authorization':'Bearer '+r.json()['access_token']})).status_code==200

@pytest.mark.asyncio
async def test_price_update_legacy_contract_and_minimum_per_currency(env):
    c,db,gid,gid2,tid=env
    u=await register(c);await login(c)
    await db.usuarios.update_one({'_id':ObjectId(u['_id'])},{'$set':{'rol':'admin'}})
    # Dos monedas de la misma tienda son ambiguas: no modificar una al azar.
    assert (await c.put(f'/juegos/{gid}/tiendas/{tid}',json={'precio':100})).status_code==409
    await c.post(f'/juegos/{gid2}/tiendas',json={'tiendaId':tid,'precio':12000,'moneda':'CLP','plataforma':'PS5'})
    updated=await c.put(f'/juegos/{gid2}/tiendas/{tid}',json={'precio':10000})
    assert updated.status_code==200,updated.text
    assert updated.json()['precio_mas_barato']['precio']==10000
    assert updated.json()['precios'][0]['plataforma']=='PS5'
    assert (await c.post(f'/juegos/{gid2}/tiendas',json={'tiendaId':tid,'precio':5,'moneda':'USD','plataforma':'PC'})).status_code==422

@pytest.mark.asyncio
async def test_registration_duplicate_race_and_admin_no_escalation(env):
    c,db,*_=env
    import asyncio
    data={'nombre':'Prueba','correo':'race@example.com','contrasena':'PruebaSegura123!','rol':'admin'}
    results=await asyncio.gather(c.post('/usuarios/',json=data),c.post('/usuarios/',json=data))
    assert sorted(r.status_code for r in results)==[201,409]
    assert await db.usuarios.count_documents({'correo':'race@example.com','rol':'admin'})==0

@pytest.mark.asyncio
async def test_rate_limits_login_and_registration(env):
    from integracion_frontend.limiter import limiter
    c,db,*_=env
    limiter.reset();limiter.enabled=True
    try:
        replies=[]
        for n in range(6):
            replies.append(await c.post('/usuarios/login',json={'correo':'nadie@example.com','contrasena':'incorrecta'}))
        assert replies[-1].status_code==429
    finally:
        limiter.enabled=False
        limiter.reset()

@pytest.mark.asyncio
async def test_openapi_auth_and_cors_unhandled_database_error(env):
    from pymongo.errors import ServerSelectionTimeoutError
    from integracion_frontend.database import get_db
    from integracion_frontend.aplicacion import app
    c,*_=env
    spec=(await c.get('/openapi.json')).json()
    assert 'HTTPBearer' in spec['components']['securitySchemes']
    def unavailable():
        raise ServerSelectionTimeoutError('simulación de prueba, dato privado que no debe mostrarse')
    before=app.dependency_overrides[get_db]
    app.dependency_overrides[get_db]=unavailable
    try:
        r=await c.get('/juegos/')
        assert r.status_code==503 and 'dato privado' not in r.text
        assert r.headers['access-control-allow-origin']=='http://localhost:5173'
    finally:
        app.dependency_overrides[get_db]=before
