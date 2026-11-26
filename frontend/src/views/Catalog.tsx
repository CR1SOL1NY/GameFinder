import { useEffect, useState } from 'react';
import { obtenerCatalogo, obtenerFiltros, type CatalogPage, type Facets } from '../api';
import { errorMessage } from '../services/http';
import { GameCard } from '../components/GameCard';
import { Empty, ErrorState, Loading } from '../components/Status';
import { fieldCls, Icon } from '../components/common';
export default function Catalog({search, navigate, priced=false}: {search: URLSearchParams; navigate: (path: string, replace?: boolean)=>void; priced?: boolean}) {
  const encoded=search.toString(), [page,setPage]=useState<CatalogPage|null>(null), [facets,setFacets]=useState<Facets>({generos:[],plataformas:[]});
  const [error,setError]=useState(''),[loading,setLoading]=useState(true),[retry,setRetry]=useState(0),[open,setOpen]=useState(false);
  const currentPage=Math.max(1,parseInt(search.get('pagina')||'1')||1), min=search.get('min')||'', max=search.get('max')||'';
  const [draftMin,setDraftMin]=useState(min),[draftMax,setDraftMax]=useState(max);
  useEffect(()=>{setDraftMin(min);setDraftMax(max);},[min,max]);
  useEffect(()=>{
    const c=new AbortController();setLoading(true);setError('');
    const p=new URLSearchParams(encoded);
    Promise.all([obtenerCatalogo({q:p.get('q')||'',genres:p.getAll('genero'),platforms:p.getAll('plataforma'),min:p.get('min')||'',max:p.get('max')||'',sort:p.get('orden')||'titulo',page:currentPage,priced},c.signal),obtenerFiltros(c.signal)]).then(([list,filters])=>{setPage(list);setFacets(filters);}).catch(e=>{if(!c.signal.aborted)setError(errorMessage(e));}).finally(()=>{if(!c.signal.aborted)setLoading(false);});
    return ()=>c.abort();
  },[encoded,currentPage,priced,retry]);
  const update=(key:string,value:string,multiple=false)=>{
    const p=new URLSearchParams(encoded);p.delete('pagina');
    if(multiple){const values=p.getAll(key);p.delete(key);(values.includes(value)?values.filter(x=>x!==value):[...values,value]).forEach(x=>p.append(key,x));}
    else if(value)p.set(key,value);else p.delete(key);
    navigate(`${priced?'/ofertas':'/catalogo'}?${p}`);
  };
  const reset=()=>navigate(priced?'/ofertas':'/catalogo');
  const filters=<aside className="h-fit rounded-xl border border-blue-500/20 bg-panel p-4 text-sm">
    <div className="mb-5 flex items-center justify-between"><h2 className="font-bold">Filtros</h2><button onClick={reset} className="text-xs text-blue-400">Limpiar todo</button></div>
    <form onSubmit={e=>{e.preventDefault();if(draftMin&&draftMax&&+draftMin>+draftMax)return;const p=new URLSearchParams(encoded);p.delete('pagina');p.delete('min');p.delete('max');if(draftMin)p.set('min',draftMin);if(draftMax)p.set('max',draftMax);navigate(`${priced?'/ofertas':'/catalogo'}?${p}`);}}>
      <p className="font-semibold">Presupuesto en CLP</p><label className="mt-3 block text-xs text-slate-400">Precio mínimo<input type="number" min={0} max={1e9} step="any" value={draftMin} onChange={e=>setDraftMin(e.target.value)} className={fieldCls}/></label><label className="mt-3 block text-xs text-slate-400">Precio máximo<input type="number" min={0} max={1e9} step="any" value={draftMax} onChange={e=>setDraftMax(e.target.value)} className={fieldCls}/></label>
      {draftMin&&draftMax&&+draftMin>+draftMax&&<p role="alert" className="mt-2 text-xs text-rose-300">El mínimo supera al máximo.</p>}<button className="mt-3 w-full rounded-lg border border-blue-500/30 py-2">Aplicar precios</button><p className="mt-2 text-xs text-slate-400">Los filtros de precio incluyen solo ofertas CLP.</p>
    </form>
    {([['genero','Géneros',facets.generos],['plataforma','Plataformas',facets.plataformas]] as const).map(([key,label,values])=><fieldset key={key} className="mt-5 border-t border-blue-500/20 pt-4"><legend className="pt-3 font-semibold">{label}</legend>{values.map(v=><label key={v} className="mt-3 flex items-center gap-2 text-slate-300"><input type="checkbox" checked={search.getAll(key).includes(v)} onChange={()=>update(key,v,true)} className="size-4 accent-blue-500"/>{v}</label>)}</fieldset>)}
  </aside>;
  return <main id="main" className="mx-auto grid max-w-[1500px] gap-5 px-4 py-6 lg:grid-cols-[240px_1fr] lg:px-8"><div className="hidden lg:block">{filters}</div><section className="min-w-0">
    <div className="rounded-xl border border-blue-500/20 bg-card p-6"><h1 className="text-2xl font-black">{priced?'Compara ofertas registradas':search.get('q')?`Resultados para “${search.get('q')}”`:'Catálogo de videojuegos'}</h1><p className="mt-2 text-sm text-slate-400">{priced?'Precios CLP disponibles, sin descuentos ni conversiones estimadas.':'Explora por género, plataforma y presupuesto.'}</p>{page&&!loading&&!error&&<p className="mt-2 text-sm text-blue-400">{page.total} {page.total===1?'juego encontrado':'juegos encontrados'}</p>}</div>
    <div className="my-4 flex flex-wrap items-center justify-between gap-3"><button onClick={()=>setOpen(!open)} aria-expanded={open} className="flex items-center gap-2 rounded-lg border border-blue-500/30 px-4 py-3 text-sm lg:hidden"><Icon name="filter"/>Filtros</button><label className="ml-auto text-sm text-slate-400">Ordenar <select value={search.get('orden')||'titulo'} onChange={e=>update('orden',e.target.value)} className="rounded-lg border border-blue-500/25 bg-field p-3 text-fg"><option value="titulo">Título A–Z</option><option value="titulo_desc">Título Z–A</option><option value="precio">Menor precio</option><option value="precio_desc">Mayor precio</option><option value="fecha">Más recientes</option></select></label></div>
    {open&&<div className="mb-5 lg:hidden">{filters}</div>}
    {loading?<Loading text="Buscando videojuegos…"/>:error?<ErrorState message={error} retry={()=>setRetry(n=>n+1)}/>:page?.items.length?<div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{page.items.map(g=><GameCard key={g.id} game={g}/>)}</div>:<Empty title="No encontramos videojuegos" text="Prueba otra búsqueda o limpia los filtros." action={reset} label="Limpiar filtros"/>}
    {!loading&&!error&&page&&page.total>24&&<nav aria-label="Paginación del catálogo" className="mt-6 flex items-center justify-center gap-4"><button disabled={currentPage===1} onClick={()=>{const p=new URLSearchParams(encoded);p.set('pagina',String(currentPage-1));navigate(`${priced?'/ofertas':'/catalogo'}?${p}`);}} className="rounded-lg border border-blue-500/30 px-4 py-3 disabled:opacity-30">Anterior</button><span className="text-sm">Página {currentPage} de {Math.ceil(page.total/24)}</span><button disabled={currentPage*24>=page.total} onClick={()=>{const p=new URLSearchParams(encoded);p.set('pagina',String(currentPage+1));navigate(`${priced?'/ofertas':'/catalogo'}?${p}`);}} className="rounded-lg bg-blue-600 px-4 py-3 text-white disabled:opacity-30">Siguiente</button></nav>}
  </section></main>;
}
