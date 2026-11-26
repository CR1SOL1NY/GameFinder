import { describe,it,expect,vi } from 'vitest';
import { mapearJuego,obtenerCatalogo } from '../src/api';
import { money,safeUrl,dateLabel } from '../src/games';
import { request,ApiError,setSessionExpiredHandler } from '../src/services/http';

describe('Datos reales y ofertas comparables',()=>{
  it('mantiene monedas, plataformas sin informar y precio cero sin inventar mínimos',()=>{
    const g=mapearJuego({_id:'abc',titulo:'Prueba sintética',generos:['RPG'],plataformas:['PS5'],precios:[{tiendaId:'t',precio:1,moneda:'USD'},{tiendaId:'t',precio:0,moneda:'CLP',plataforma:'PS5'},{tiendaId:'t',precio:-5,moneda:'CLP'},{tiendaId:'t',precio:Infinity,moneda:'CLP'}]},[{_id:'t',nombre:'Tienda de prueba'}]);
    expect(g.offers).toHaveLength(2);expect(g.price).toBe(0);expect(g.offers[0].platform).toBeUndefined();expect(g.offers[1].platform).toBe('PS5');expect(g.bestStore).toBe('Tienda de prueba');
  });
  it('no transforma un precio faltante en gratis',()=>{expect(mapearJuego({_id:'a',titulo:'Prueba'},[]).price).toBeNull();expect(money(null)).toBe('Precio no disponible');expect(money(0)).toContain('0');});
  it('conserva la fecha calendario del lanzamiento',()=>{expect(dateLabel('2025-01-01T00:00:00Z',true)).toContain('2025');});
  it('rechaza enlaces ejecutables y enlaces con credenciales',()=>{expect(safeUrl('javascript:alert(1)')).toBeUndefined();expect(safeUrl('https://user:password@example.com')).toBeUndefined();expect(safeUrl('https://example.com/game')).toBe('https://example.com/game');});
  it('combina filtros y paginación en solicitudes reales de servicio',async()=>{
    const urls:string[]=[];
    vi.stubGlobal('fetch',vi.fn(async(url:string)=>{urls.push(url);return new Response(JSON.stringify(url.includes('/tiendas/')?[]:{items:[],total:0,limit:24,skip:24}),{status:200});}));
    await obtenerCatalogo({q:'Alfa',genres:['RPG','Acción'],platforms:['PC'],min:'0',max:'20000',page:2,sort:'precio'});
    const query=new URL(urls.find(x=>x.includes('/catalogo'))!).searchParams;
    expect(query.getAll('genero')).toEqual(['RPG','Acción']);expect(query.get('plataforma')).toBe('PC');expect(query.get('skip')).toBe('24');expect(query.get('precio_min')).toBe('0');expect(query.get('q')).toBe('Alfa');
    vi.unstubAllGlobals();
  });
});

describe('Manejo de fallos HTTP',()=>{
  it('no devuelve éxito cuando FastAPI falla',async()=>{vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({detail:'Base no disponible'}),{status:503})));await expect(request('/juegos/')).rejects.toThrow('Base no disponible');vi.unstubAllGlobals();});
  it('informa respuestas exitosas con contenido inválido',async()=>{vi.stubGlobal('fetch',vi.fn(async()=>new Response('<html>proxy incorrecto</html>',{status:200})));await expect(request('/juegos/')).rejects.toThrow('no pudimos interpretar');vi.unstubAllGlobals();});
  it('informa fallos de red',async()=>{vi.stubGlobal('fetch',vi.fn(async()=>{throw new TypeError('Failed to fetch');}));await expect(request('/juegos/')).rejects.toThrow('No pudimos conectar');vi.unstubAllGlobals();});
  it('maneja sesiones vencidas sin borrar un login fallido',async()=>{const expired=vi.fn();setSessionExpiredHandler(expired);vi.stubGlobal('fetch',vi.fn(async()=>new Response('{}',{status:401})));await expect(request('/usuarios/abc/deseados')).rejects.toBeInstanceOf(ApiError);expect(expired).toHaveBeenCalledOnce();await expect(request('/usuarios/login')).rejects.toBeInstanceOf(ApiError);expect(expired).toHaveBeenCalledOnce();vi.unstubAllGlobals();setSessionExpiredHandler(()=>{});});
});

describe('Información adicional opcional de la ficha', () => {
  it('conserva solo características y requisitos efectivamente informados por la API', () => {
    const g = mapearJuego({ _id: 'extra', titulo: 'Prueba sintética', descripcionCorta: ' Resumen real del fixture ', imagenFondo: 'https://example.com/fondo.jpg', caracteristicas: ['Exploración', 'Combate', 'Exploración', ''], requisitosSistema: { plataforma: 'PC', minimos: { memoria: '8 GB del fixture' }, recomendados: { procesador: 'CPU del fixture' } } }, []);
    expect(g.summary).toBe('Resumen real del fixture');
    expect(g.backgroundUrl).toBe('https://example.com/fondo.jpg');
    expect(g.features).toEqual(['Exploración', 'Combate']);
    expect(g.systemRequirements).toMatchObject({ plataforma: 'PC', minimos: { memoria: '8 GB del fixture' }, recomendados: { procesador: 'CPU del fixture' } });
    expect(g.systemRequirements?.minimos?.procesador).toBeUndefined();
  });
  it('no copia información de otros juegos y rechaza formatos y enlaces de fondo inválidos', () => {
    const g = mapearJuego({ _id: 'incompleto', titulo: 'Prueba incompleta', imagenFondo: 'javascript:alert(1)', requisitosSistema: { minimos: {} } }, []);
    expect(g.backgroundUrl).toBeUndefined();
    expect(g.systemRequirements).toBeUndefined();
    expect(g.features).toEqual([]);
    expect(g.summary).toBeUndefined();
  });
});
