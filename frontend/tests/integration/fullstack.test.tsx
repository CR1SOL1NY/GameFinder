/** React → HTTP → FastAPI → MongoDB de prueba, real (local/Atlas) o emulado según el ejecutor; sin navegador real. */
import { beforeEach,afterEach,it,expect,vi } from 'vitest';
import { render,screen,within,waitFor,fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../../src/App';
const realFetch=globalThis.fetch;
const api='http://127.0.0.1:8017/interfaz';
let cookie='';
beforeEach(async()=>{
  cookie='';
  await realFetch(`${api}/__tests__/reset`,{method:'POST'});
  history.replaceState(null,'','/catalogo');
  localStorage.clear();sessionStorage.clear();
  vi.stubGlobal('fetch',async(input:string|URL|Request,init:RequestInit={})=>{
    const headers=new Headers(init.headers);headers.set('Origin','http://localhost:5173');if(cookie)headers.set('Cookie',cookie);
    const response=await realFetch(input,{...init,headers});
    const cookies=response.headers.getSetCookie();
    if(cookies.length)cookie=cookies.map(c=>c.split(';')[0]).join('; ');
    return response;
  });
});
afterEach(()=>vi.unstubAllGlobals());

async function registerFromDialog(u:ReturnType<typeof userEvent.setup>){
  const dialog=await screen.findByRole('dialog');
  await u.click(within(dialog).getByRole('button',{name:'¿No tienes cuenta? Regístrate'}));
  await u.type(within(dialog).getByLabelText('Nombre'),'Persona Prueba');
  await u.type(within(dialog).getByLabelText('Correo electrónico'),'persona@example.com');
  await u.type(within(dialog).getByLabelText('Contraseña'),'PruebaSegura123!');
  await u.click(within(dialog).getByRole('button',{name:'Crear cuenta'}));
  await waitFor(()=>expect(screen.queryByRole('dialog')).toBeNull());
}

it('registro, lista persistente tras logout/login, perfil y calificación guardados vía FastAPI',async()=>{
  // Conserva HTTP real, pero retiene la respuesta de opciones del perfil hasta
  // que el formulario ya esté abierto: reproduce una conexión lenta a Atlas.
  const httpFetch=globalThis.fetch;
  let holdPreferences=false;
  let releasePreferences!:()=>void;
  const preferencesReady=new Promise<void>(resolve=>{releasePreferences=resolve;});
  vi.stubGlobal('fetch',async(input:string|URL|Request,init?:RequestInit)=>{
    const response=await httpFetch(input,init);
    if(holdPreferences&&new URL(String(input)).pathname.endsWith('/juegos/filtros'))await preferencesReady;
    return response;
  });
  const u=userEvent.setup();render(<App/>);
  await screen.findByRole('heading',{name:'Catálogo de videojuegos'});
  await screen.findByRole('button',{name:'Ver Juego de prueba Alfa'});
  const card=screen.getByRole('button',{name:'Ver Juego de prueba Alfa'}).closest('article')!;
  await u.click(within(card).getByRole('button',{name:'Añadir a la lista de deseados'}));
  await registerFromDialog(u);
  await waitFor(()=>expect(within(card).getByRole('button',{name:'Quitar de la lista de deseados'})).toBeTruthy());
  expect(sessionStorage.getItem('gf-session')).toBeNull();expect(localStorage.getItem('gf-session')).toBeNull();
  await u.click(screen.getByRole('button',{name:'Ver Juego de prueba Alfa'}));
  await screen.findByRole('heading',{name:'Juego de prueba Alfa'});
  expect(screen.getByRole('table').textContent).toContain('15.000');
  expect(screen.getByRole('table').textContent).toContain('Tienda de prueba (datos sintéticos)');
  await u.click(screen.getByRole('tab',{name:'Reseñas'}));
  await u.click(await screen.findByRole('button',{name:'Calificar este juego'}));
  await u.click(screen.getByRole('radio',{name:'4 de 5 estrellas'}));
  await u.type(screen.getByLabelText('Comentario (opcional)'),'Reseña sintética guardada vía HTTP.');
  await u.click(screen.getByRole('button',{name:'Guardar calificación'}));
  await screen.findByText('Reseña sintética guardada vía HTTP.');
  const header=document.querySelector('header')!;
  await u.click(within(header).getByRole('button',{name:'Perfil'}));
  await screen.findByRole('heading',{name:'Persona Prueba'});
  holdPreferences=true;
  await u.click(screen.getByRole('button',{name:'Editar perfil y preferencias'}));
  const name=screen.getByLabelText('Nombre');await u.clear(name);await u.type(name,'Nombre Actualizado');
  expect(within(screen.getByRole('group',{name:'Géneros que te interesan'})).queryByRole('button',{name:'RPG'})).toBeNull();
  releasePreferences();
  await u.click(await within(screen.getByRole('group',{name:'Géneros que te interesan'})).findByRole('button',{name:'RPG'},{timeout:15000}));
  await u.click(await within(screen.getByRole('group',{name:'Plataformas favoritas'})).findByRole('button',{name:'PC'}));
  await u.click(screen.getByRole('button',{name:'Guardar cambios'}));
  await waitFor(()=>expect(screen.getByRole('status').textContent).toContain('Perfil y preferencias guardados'));
  await u.click(screen.getByRole('button',{name:'Cerrar sesión'}));
  await screen.findByRole('button',{name:'Iniciar sesión o crear cuenta'});
  await u.click(screen.getByRole('button',{name:'Iniciar sesión o crear cuenta'}));
  const dialog=await screen.findByRole('dialog');await u.type(within(dialog).getByLabelText('Correo electrónico'),'persona@example.com');await u.type(within(dialog).getByLabelText('Contraseña'),'PruebaSegura123!');await u.click(within(dialog).getByRole('button',{name:'Iniciar sesión'}));
  await screen.findByRole('heading',{name:'Nombre Actualizado'});
  const restored=await fetch(`${api}/usuarios/me`);
  expect(restored.status).toBe(200);
  expect((await restored.json()).preferencias).toMatchObject({generos:['RPG'],plataformas:['PC']});
  await u.click(within(screen.getByRole('navigation',{name:'Secciones de tu cuenta'})).getByRole('button',{name:'Lista de deseados',exact:true}));
  await screen.findByRole('button',{name:'Ver Juego de prueba Alfa'});
  await u.click(screen.getByRole('button',{name:'Mis calificaciones'}));
  await screen.findByText('Reseña sintética guardada vía HTTP.');
});

it('combina búsqueda, género y plataforma y muestra el estado vacío',async()=>{
  const u=userEvent.setup();render(<App/>);
  await screen.findByRole('button',{name:'Ver Juego de prueba Alfa'});
  const search=screen.getByRole('textbox',{name:'Buscar juegos'});await u.type(search,'Alfa{Enter}');
  await screen.findByRole('heading',{name:'Resultados para “Alfa”'});
  const genres=screen.getAllByLabelText('RPG');await u.click(genres[0]);
  await waitFor(()=>expect(location.search).toContain('genero=RPG'));
  const platform=screen.getAllByLabelText('PC');await u.click(platform[0]);
  await waitFor(()=>expect(location.search).toContain('plataforma=PC'));
  expect(await screen.findByText('1 juego encontrado')).toBeTruthy();
  await u.click(screen.getAllByLabelText('PS5')[0]);
  await u.click(screen.getAllByLabelText('PC')[0]);
  await screen.findByRole('heading',{name:'No encontramos videojuegos'});
  await u.click(screen.getByRole('button',{name:'Limpiar filtros'}));
  await screen.findByRole('button',{name:'Ver Juego de prueba Beta'});
});

it.each(['/catalogo', '/ofertas'])('conserva filtros, presupuesto y orden al buscar y borrar el texto en %s', async (path) => {
  const filters = 'genero=RPG&genero=Estrategia&plataforma=PC&plataforma=PS5&min=1000&max=20000&orden=precio_desc';
  history.replaceState(null, '', `${path}?${filters}&pagina=2`);
  const u = userEvent.setup(); render(<App />);
  await screen.findByRole('heading', { name: 'No encontramos videojuegos' });
  const search = screen.getByRole('textbox', { name: 'Buscar juegos' });
  await u.type(search, 'Alfa{Enter}');
  await screen.findByRole('button', { name: 'Ver Juego de prueba Alfa' });
  const expected = new URLSearchParams(filters);
  expected.set('q', 'Alfa');
  expect(location.pathname).toBe(path);
  expect(new URLSearchParams(location.search)).toEqual(expected);
  expect(screen.getByLabelText('RPG')).toHaveProperty('checked', true);
  expect(screen.getByLabelText('Estrategia')).toHaveProperty('checked', true);
  expect(screen.getByLabelText('PC')).toHaveProperty('checked', true);
  expect(screen.getByLabelText('PS5')).toHaveProperty('checked', true);
  expect(screen.getByLabelText('Precio mínimo')).toHaveProperty('value', '1000');
  expect(screen.getByLabelText('Precio máximo')).toHaveProperty('value', '20000');
  expect(screen.getByLabelText('Ordenar')).toHaveProperty('value', 'precio_desc');
  expect(screen.queryByRole('button', { name: 'Ver Juego de prueba Comparación' })).toBeNull();

  await u.clear(search);
  await u.click(screen.getByRole('button', { name: 'Buscar', exact: true }));
  await screen.findByRole('button', { name: 'Ver Juego de prueba Comparación' });
  expect(location.pathname).toBe(path);
  expect(new URLSearchParams(location.search)).toEqual(new URLSearchParams(filters));
  expect(screen.queryByRole('button', { name: 'Ver Juego de prueba Beta' })).toBeNull();

  await u.click(screen.getByRole('button', { name: 'Ver Juego de prueba Alfa' }));
  await screen.findByRole('heading', { name: 'Juego de prueba Alfa' });
  await u.click(screen.getByRole('button', { name: /Volver/ }));
  await screen.findByRole('button', { name: 'Ver Juego de prueba Comparación' });
  expect(location.pathname).toBe(path);
  expect(new URLSearchParams(location.search)).toEqual(new URLSearchParams(filters));
});

it('conserva el texto que estás escribiendo cuando cambias un filtro', async () => {
  const u = userEvent.setup(); render(<App />);
  await screen.findByRole('button', { name: 'Ver Juego de prueba Alfa' });
  const search = screen.getByRole('textbox', { name: 'Buscar juegos' });
  await u.type(search, 'Alfa');
  await u.click(screen.getByLabelText('RPG'));
  await screen.findByText('1 juego encontrado');
  expect(search).toHaveProperty('value', 'Alfa');
  await u.click(screen.getByRole('button', { name: 'Buscar', exact: true }));
  await screen.findByRole('heading', { name: 'Resultados para “Alfa”' });
  expect(new URLSearchParams(location.search).get('genero')).toBe('RPG');
});

it('la navegación y el error de conexión conservan acceso a la cuenta',async()=>{
  history.replaceState(null,'','/');
  vi.stubGlobal('fetch',vi.fn(async()=>{throw new TypeError('Fallo de red simulado en prueba');}));
  const u=userEvent.setup();render(<App/>);
  await screen.findByRole('button',{name:'Volver a intentar'});
  await u.click(within(document.querySelector('header')!).getByRole('button',{name:'Perfil'}));
  await screen.findByRole('button',{name:'Iniciar sesión o crear cuenta'});
  expect(screen.getByRole('heading',{name:'Tu perfil de GameFinder'})).toBeTruthy();
});

it('compara por plataforma y moneda con las ofertas recibidas de FastAPI', async () => {
  const u = userEvent.setup();
  render(<App />);
  await u.click(await screen.findByRole('button', { name: 'Ver Juego de prueba Comparación' }));
  await screen.findByRole('heading', { name: 'Juego de prueba Comparación' });
  const rows = () => within(screen.getByRole('table'));
  expect(rows().getByText('Tienda PC de prueba')).toBeTruthy();
  expect(rows().queryByText('Tienda PS5 de prueba')).toBeNull();
  expect(rows().queryByText('Tienda sin plataforma de prueba')).toBeNull();
  await u.click(screen.getByRole('radio', { name: 'PS5' }));
  expect(rows().getByText('Tienda PS5 de prueba')).toBeTruthy();
  expect(rows().queryByText('Tienda PC de prueba')).toBeNull();
  expect(rows().getByText('Más barato').closest('tr')?.textContent).toContain('10.000');
  await u.click(screen.getByRole('radio', { name: 'Xbox' }));
  expect(screen.queryByRole('table')).toBeNull();
  expect(screen.getByRole('heading', { name: 'Sin ofertas para Xbox' })).toBeTruthy();
  await u.click(screen.getByRole('radio', { name: 'Sin plataforma informada (1)' }));
  expect(rows().getByText('Tienda sin plataforma de prueba')).toBeTruthy();
  expect(rows().queryByText('Más barato')).toBeNull();
  await u.click(screen.getByRole('radio', { name: 'PC' }));
  await u.selectOptions(screen.getByLabelText('Moneda'), 'USD');
  expect(rows().getByText('Tienda USD de prueba')).toBeTruthy();
  expect(rows().queryByText('Tienda PC de prueba')).toBeNull();
  expect(rows().queryByText('Tienda sin plataforma de prueba')).toBeNull();
});


it('guarda y edita precios de la misma tienda por plataforma desde Administración', async () => {
  const u = userEvent.setup();
  const login = await fetch(`${api}/usuarios/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ correo: 'admin-test@example.com', contrasena: 'ClaveSoloPruebas123!' }) });
  expect(login.status).toBe(200);
  history.replaceState(null, '', '/admin');
  render(<App />);
  const adminNav = await screen.findByRole('navigation', { name: 'Secciones de administración' });
  await u.click(within(adminNav).getByRole('button', { name: 'Ofertas', exact: true }));
  await screen.findByRole('option', { name: 'Juego de prueba Comparación' });
  await u.selectOptions(await screen.findByLabelText('Juego'), '000000000000000000000003');
  await screen.findByRole('heading', { name: 'Precios por plataforma' });
  await u.selectOptions(screen.getByLabelText('Tienda'), '000000000000000000000011');
  await u.selectOptions(screen.getByLabelText('Plataforma de esta oferta'), 'PS5');
  await u.type(screen.getByLabelText('Precio'), '28000');
  await u.click(screen.getByRole('button', { name: 'Crear oferta para esta plataforma' }));
  await waitFor(() => expect(screen.getByRole('status').textContent).toContain('Oferta guardada'));
  await screen.findByRole('button', { name: 'Crear oferta para esta plataforma' });
  // El precio nuevo de PS5 convive con PC en la misma tienda.
  const path = `${api}/juegos/000000000000000000000003/ofertas`;
  let result = await (await fetch(`${path}?plataforma=PS5&moneda=CLP`)).json();
  expect(result.ofertas.map((p: { precio: number }) => p.precio)).toEqual([10000, 28000]);
  const target = result.ofertas.find((p: { tiendaId: string }) => p.tiendaId === '000000000000000000000011');
  expect(target.ofertaId).toBeTruthy();
  await u.selectOptions(screen.getByLabelText('Oferta'), '4');
  expect((screen.getByLabelText('Plataforma de esta oferta') as HTMLSelectElement).value).toBe('PS5');
  await u.clear(screen.getByLabelText('Precio'));
  await u.type(screen.getByLabelText('Precio'), '26000');
  await u.click(screen.getByRole('button', { name: 'Guardar cambios de esta oferta' }));
  await screen.findByRole('button', { name: 'Crear oferta para esta plataforma' });
  result = await (await fetch(`${path}?plataforma=PS5&moneda=CLP`)).json();
  expect(result.ofertas.find((p: { ofertaId: string }) => p.ofertaId === target.ofertaId).precio).toBe(26000);
  const pc = await (await fetch(`${path}?plataforma=PC&moneda=CLP`)).json();
  expect(pc.ofertas[0].precio).toBe(20000);
  // Una oferta heredada sin ID también se puede clasificar sin alterar su precio.
  await u.selectOptions(screen.getByLabelText('Oferta'), '2');
  await u.selectOptions(screen.getByLabelText('Plataforma de esta oferta'), 'Xbox');
  await u.click(screen.getByRole('button', { name: 'Guardar cambios de esta oferta' }));
  await screen.findByRole('button', { name: 'Crear oferta para esta plataforma' });
  const xbox = await (await fetch(`${path}?plataforma=Xbox&moneda=CLP`)).json();
  expect(xbox.ofertas[0].precio).toBe(5000);
  expect(xbox.ofertas[0].ofertaId).toBeTruthy();
});

it('perfil muestra datos reales, tres reseñas, comparaciones y enlaces a las listas completas', async () => {
  async function post(path: string, body?: unknown) {
    return fetch(`${api}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
  }
  // Se amplía únicamente la base descartable a través de sus endpoints administrativos.
  expect((await post('/usuarios/login', { correo: 'admin-test@example.com', contrasena: 'ClaveSoloPruebas123!' })).status).toBe(200);
  const created = await post('/juegos/', { titulo: 'Juego de prueba Extra', plataformas: ['PC'], generos: [] });
  expect(created.status).toBe(201);
  const extraId = (await created.json())._id;
  await post('/usuarios/logout');
  const registration = await post('/usuarios/', { nombre: 'Perfil de Prueba', correo: 'perfil@example.com', contrasena: 'PruebaSegura123!', preferencias: { generos: ['RPG'], plataformas: ['PC'], precioMin: 5000, precioMax: 50000 } });
  expect(registration.status).toBe(201);
  const accountId = (await registration.json())._id;
  expect((await post('/usuarios/login', { correo: 'perfil@example.com', contrasena: 'PruebaSegura123!' })).status).toBe(200);
  const games = [
    ['000000000000000000000001', 'Juego de prueba Alfa'],
    ['000000000000000000000002', 'Juego de prueba Beta'],
    ['000000000000000000000003', 'Juego de prueba Comparación'],
    [extraId, 'Juego de prueba Extra'],
  ];
  for (let i = 0; i < games.length; i++) {
    expect((await post('/calificaciones/', { juegoId: games[i][0], puntaje: 5 - i, comentario: `Reseña HTTP ${i + 1}` })).status).toBe(201);
  }
  expect((await fetch(`${api}/usuarios/${accountId}/deseados/${games[0][0]}`, { method: 'PUT' })).status).toBe(200);
  const u = userEvent.setup();
  const view = render(<App />);
  // Abrir solo la ficha por la portada no equivale a pulsar Comparar precios.
  await u.click(await screen.findByRole('button', { name: 'Ver Juego de prueba Alfa' }));
  await screen.findByRole('heading', { name: 'Juego de prueba Alfa' });
  expect(localStorage.getItem(`gf-comparisons-v1:${accountId}`)).toBeNull();
  await u.click(screen.getByRole('button', { name: 'Volver al catálogo' }));
  for (const [, title] of games) {
    await screen.findByRole('heading', { name: 'Catálogo de videojuegos' });
    const card = (await screen.findByRole('button', { name: `Ver ${title}` })).closest('article')!;
    await u.click(within(card).getByRole('button', { name: 'Comparar precios', exact: true }));
    await screen.findByRole('heading', { name: title });
    await u.click(screen.getByRole('button', { name: 'Volver al catálogo' }));
  }
  await u.click(within(document.querySelector('header')!).getByRole('button', { name: 'Perfil' }));
  await screen.findByRole('heading', { name: 'Perfil de Prueba' });
  const stats = within(screen.getByRole('group', { name: 'Estadísticas de tu perfil' }));
  await stats.findByText('3,5');
  expect(stats.getByRole('button', { name: /Juegos en tu lista de deseados/ }).textContent).toContain('1');
  expect(stats.getByRole('button', { name: /Juegos comparados/ }).textContent).toContain('4');
  const reviews = within(screen.getByRole('region', { name: 'Últimas reseñas' }));
  expect(reviews.getAllByRole('article')).toHaveLength(3);
  expect(reviews.queryByText('Reseña HTTP 1')).toBeNull();
  expect(reviews.getByText('Reseña HTTP 4')).toBeTruthy();
  const activity = within(screen.getByRole('region', { name: 'Tu actividad reciente' }));
  await activity.findByText('Juego de prueba Extra');
  expect(activity.getAllByRole('listitem')).toHaveLength(3);
  expect(activity.queryByText('Juego de prueba Alfa')).toBeNull();
  await u.click(reviews.getByRole('button', { name: /Ver todas las reseñas/ }));
  await screen.findByRole('heading', { name: 'Mis calificaciones' });
  await screen.findByText('Reseña HTTP 1');
  expect(screen.getAllByRole('article')).toHaveLength(4);
  expect(location.pathname).toBe('/perfil/calificaciones');
  await u.click(within(screen.getByRole('navigation', { name: 'Secciones de tu cuenta' })).getByRole('button', { name: 'Mi perfil', exact: true }));
  await u.click(await screen.findByRole('button', { name: /Ver todos los juegos comparados/ }));
  await screen.findByRole('heading', { name: 'Juegos comparados (4)' });
  await screen.findByText('Juego de prueba Alfa');
  expect(location.pathname).toBe('/perfil/comparados');
  view.unmount();
  // Los registros permanecen al recargar y otra cuenta no ve esa actividad.
  const reloaded = render(<App />);
  await screen.findByRole('heading', { name: 'Juegos comparados (4)' });
  reloaded.unmount();
  await post('/usuarios/logout');
  await post('/usuarios/', { nombre: 'Otro Perfil', correo: 'otro-perfil@example.com', contrasena: 'PruebaSegura123!' });
  await post('/usuarios/login', { correo: 'otro-perfil@example.com', contrasena: 'PruebaSegura123!' });
  history.replaceState(null, '', '/perfil');
  render(<App />);
  await screen.findByRole('heading', { name: 'Otro Perfil' });
  await screen.findByText('Todavía no has publicado reseñas. Califica un juego desde su ficha.');
  expect(screen.getByText('Tu próxima comparación aparecerá aquí')).toBeTruthy();
  expect(screen.queryByText('Reseña HTTP 4')).toBeNull();
});

it('guarda medias estrellas y avisa de una bajada real de precio de un deseado', async () => {
  const register = await fetch(`${api}/usuarios/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nombre: 'Persona Avisos', correo: 'avisos@example.com', contrasena: 'PruebaSegura123!' }) });
  expect(register.status).toBe(201);
  const uid = (await register.json())._id;
  const login = await fetch(`${api}/usuarios/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ correo: 'avisos@example.com', contrasena: 'PruebaSegura123!' }) });
  expect(login.status).toBe(200);
  const gid = '000000000000000000000001';
  expect((await fetch(`${api}/usuarios/${uid}/deseados/${gid}`, { method: 'PUT' })).status).toBe(200);
  const u = userEvent.setup();
  render(<App />);
  await screen.findByRole('button', { name: 'Ver Juego de prueba Alfa' });
  await waitFor(() => expect(JSON.parse(localStorage.getItem(`gf-price-alerts-v1:${uid}`) || '{}').checkedAt).toBeTruthy());
  await u.click(within(document.querySelector('header')!).getByRole('button', { name: 'Notificaciones', exact: true }));
  await screen.findByText('Sin bajadas de precio detectadas');
  // El admin de la base emulada actualiza el precio sin sustituir la sesión del usuario.
  const adminLogin = await realFetch(`${api}/usuarios/login`, { method: 'POST', headers: { 'Content-Type': 'application/json', Origin: 'http://localhost:5173' }, body: JSON.stringify({ correo: 'admin-test@example.com', contrasena: 'ClaveSoloPruebas123!' }) });
  expect(adminLogin.status).toBe(200);
  const adminToken = (await adminLogin.json()).access_token;
  const changed = await realFetch(`${api}/juegos/${gid}/tiendas/000000000000000000000010?plataforma=PC&moneda=CLP`, { method: 'PUT', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${adminToken}` }, body: JSON.stringify({ precio: 12000 }) });
  expect(changed.status).toBe(200);
  const popup = within(screen.getByRole('dialog', { name: 'Notificaciones de precios' }));
  await u.click(popup.getByRole('button', { name: 'Actualizar precios' }));
  await popup.findByText('Juego de prueba Alfa bajó de precio');
  expect(screen.getByRole('button', { name: 'Notificaciones (1 sin leer)', exact: true })).toBeTruthy();
  expect(popup.getByText('$15.000')).toBeTruthy();
  await u.click(popup.getByRole('button', { name: /Juego de prueba Alfa bajó de precio/ }));
  await screen.findByRole('heading', { name: 'Juego de prueba Alfa' });
  expect(screen.getByRole('table').textContent).toContain('12.000');
  await u.click(screen.getByRole('tab', { name: 'Reseñas' }));
  await u.click(await screen.findByRole('button', { name: 'Calificar este juego' }));
  await u.click(screen.getByRole('radio', { name: '3,5 de 5 estrellas' }));
  await u.type(screen.getByLabelText('Comentario (opcional)'), 'Reseña con media estrella vía HTTP.');
  await u.click(screen.getByRole('button', { name: 'Guardar calificación' }));
  await screen.findByText('Reseña con media estrella vía HTTP.');
  await screen.findByRole('img', { name: '3,5 de 5 estrellas' });
  expect((await (await fetch(`${api}/calificaciones/mia/${gid}`)).json()).puntaje).toBe(3.5);
  await u.click(within(document.querySelector('header')!).getByRole('button', { name: 'Perfil' }));
  const reviews = within(await screen.findByRole('region', { name: 'Últimas reseñas' }));
  await reviews.findByRole('img', { name: '3,5 de 5 estrellas' });
  expect(screen.queryByText('Géneros preferidos')).toBeNull();
});


it('la ficha muestra información ampliada real de FastAPI y conserva reseñas, deseados y comparador lateral', async () => {
  const u = userEvent.setup();
  render(<App />);
  await u.click(await screen.findByRole('button', { name: 'Ver Juego de prueba Alfa' }));
  await screen.findByRole('heading', { name: 'Juego de prueba Alfa' });
  expect(screen.getByText('Resumen breve sintético de la ficha')).toBeTruthy();
  expect(screen.getByText('Exploración sintética de prueba')).toBeTruthy();
  expect(screen.getByText('CPU mínima de prueba')).toBeTruthy();
  expect(screen.getByText('CPU recomendada de prueba')).toBeTruthy();
  expect(screen.getByRole('heading', { name: 'Requisitos del sistema (PC)' })).toBeTruthy();
  expect(within(screen.getByRole('tablist')).getAllByRole('tab').map(tab => tab.textContent)).toEqual(['Información', 'Reseñas']);
  const sidebar = within(screen.getByRole('complementary', { name: 'Tiendas y precios del videojuego' }));
  expect(sidebar.getByRole('table').textContent).toContain('15.000');
  const hero = within(screen.getByRole('region', { name: 'Presentación del videojuego' }));
  await u.click(hero.getByRole('button', { name: 'Añadir a la lista de deseados' }));
  await registerFromDialog(u);
  await hero.findByRole('button', { name: 'Quitar de la lista de deseados' });
  expect(hero.getByText('En tu lista de deseados')).toBeTruthy();
  await u.click(hero.getByRole('button', { name: /Sin reseñas todavía/ }));
  await screen.findByRole('heading', { name: 'Calificaciones de la comunidad' });
  expect(screen.getByRole('tab', { name: 'Reseñas' }).getAttribute('aria-selected')).toBe('true');
  expect(sidebar.getByRole('table')).toBeTruthy();
});

it('edita una ficha desde Administración, la vuelve a cargar y muestra los cambios guardados por FastAPI', async () => {
  const u = userEvent.setup();
  const gid = '000000000000000000000001';
  expect((await fetch(`${api}/usuarios/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ correo: 'admin-test@example.com', contrasena: 'ClaveSoloPruebas123!' }) })).status).toBe(200);
  const before = await (await fetch(`${api}/juegos/${gid}`)).json();
  history.replaceState(null, '', '/admin');
  const view = render(<App />);
  await screen.findByRole('option', { name: 'Juego de prueba Alfa' });
  await u.selectOptions(screen.getByLabelText('Juego'), gid);
  const summary = await screen.findByLabelText('Resumen del encabezado', { exact: false });
  await u.clear(summary); await u.type(summary, 'Resumen editado y guardado vía HTTP');
  const features = screen.getByLabelText('Características del juego', { exact: false });
  await u.clear(features); await u.type(features, 'Característica verificada en prueba HTTP');
  const memory = within(screen.getByRole('group', { name: 'Mínimos' })).getByLabelText('Memoria');
  await u.clear(memory); await u.type(memory, 'Memoria editada en prueba HTTP');
  await u.click(screen.getByRole('button', { name: 'Guardar juego' }));
  await waitFor(() => expect(screen.getByRole('status').textContent).toContain('Juego guardado'));
  const stored = await (await fetch(`${api}/juegos/${gid}`)).json();
  expect(stored.descripcionCorta).toBe('Resumen editado y guardado vía HTTP');
  expect(stored.caracteristicas).toEqual(['Característica verificada en prueba HTTP']);
  expect(stored.requisitosSistema.minimos.memoria).toBe('Memoria editada en prueba HTTP');
  expect(stored.requisitosSistema.recomendados).toEqual(before.requisitosSistema.recomendados);
  expect(stored.precios).toEqual(before.precios);
  expect(stored.imagenFondo).toBe(before.imagenFondo);
  expect(stored.fechaLanzamiento).toBe(before.fechaLanzamiento);
  view.unmount();
  history.replaceState(null, '', '/admin');
  const reopened = render(<App />);
  await screen.findByRole('option', { name: 'Juego de prueba Alfa' });
  await u.selectOptions(screen.getByLabelText('Juego'), gid);
  expect(await screen.findByLabelText('Resumen del encabezado', { exact: false })).toHaveProperty('value', stored.descripcionCorta);
  reopened.unmount();
  history.replaceState(null, '', '/catalogo');
  render(<App />);
  await u.click(await screen.findByRole('button', { name: 'Ver Juego de prueba Alfa' }));
  await screen.findByText('Resumen editado y guardado vía HTTP');
  expect(screen.getByText('Característica verificada en prueba HTTP')).toBeTruthy();
  expect(screen.getByText('Memoria editada en prueba HTTP')).toBeTruthy();
  expect(screen.getByRole('table').textContent).toContain('15.000');
});

it('configura plataformas de una tienda y valida sus ofertas desde React y FastAPI', async () => {
  const u = userEvent.setup();
  const tid = '000000000000000000000011', gid = '000000000000000000000003';
  expect((await fetch(`${api}/usuarios/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ correo: 'admin-test@example.com', contrasena: 'ClaveSoloPruebas123!' }) })).status).toBe(200);
  const before = await (await fetch(`${api}/juegos/${gid}`)).json();
  history.replaceState(null, '', '/admin'); render(<App />);
  const nav = await screen.findByRole('navigation', { name: 'Secciones de administración' });
  await u.click(within(nav).getByRole('button', { name: 'Tiendas', exact: true }));
  await screen.findByRole('option', { name: 'Tienda PC de prueba' });
  await u.selectOptions(screen.getByLabelText('Tienda'), tid);
  await u.click(screen.getByLabelText('Configurar plataformas de esta tienda'));
  await u.type(screen.getByLabelText('Añadir plataforma'), 'PC');
  await u.click(screen.getByRole('button', { name: 'Añadir plataforma', exact: true }));
  await u.click(screen.getByRole('button', { name: 'Guardar tienda' }));
  await waitFor(() => expect(screen.getByRole('status').textContent).toContain('Tienda guardada'));
  expect((await (await fetch(`${api}/tiendas/${tid}`)).json()).plataformas).toEqual(['PC']);
  expect((await (await fetch(`${api}/juegos/${gid}`)).json()).precios).toEqual(before.precios);
  await u.click(within(nav).getByRole('button', { name: 'Ofertas', exact: true }));
  await u.selectOptions(screen.getByLabelText('Juego'), gid);
  await screen.findByRole('heading', { name: 'Precios por plataforma' });
  await u.selectOptions(screen.getByLabelText('Oferta'), '0');
  const platforms = screen.getByLabelText('Plataforma de esta oferta');
  await waitFor(() => expect(within(platforms).getAllByRole('option').map(o => (o as HTMLOptionElement).value)).toEqual(['', 'PC']));
  const rejected = await fetch(`${api}/juegos/${gid}/ofertas`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tiendaId: tid, plataforma: 'PS5', precio: 123 }) });
  expect(rejected.status).toBe(422);
  await u.clear(screen.getByLabelText('Precio')); await u.type(screen.getByLabelText('Precio'), '18000');
  await u.click(screen.getByRole('button', { name: 'Guardar cambios de esta oferta' }));
  await waitFor(() => expect(screen.getByRole('status').textContent).toContain('Oferta guardada'));
  const saved = (await (await fetch(`${api}/juegos/${gid}`)).json()).precios;
  expect(saved.find((p: { tiendaId: string }) => p.tiendaId === tid).precio).toBe(18000);
  expect(saved.filter((p: { tiendaId: string }) => p.tiendaId !== tid)).toEqual(before.precios.filter((p: { tiendaId: string }) => p.tiendaId !== tid));
});
