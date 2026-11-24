import { useEffect, useState } from 'react';
import { useStore } from '../context/Store';
import { obtenerCatalogoAdmin, obtenerJuegoAdmin, obtenerTiendas, type TiendaAPI } from '../api';
import { request, errorMessage } from '../services/http';
import { type Game, dateLabel } from '../games';
import OfferEditor from '../components/OfferEditor';
import GameEditor from '../components/GameEditor';
import StoreEditor from '../components/StoreEditor';
import { Empty, ErrorState } from '../components/Status';
import { panel, fieldCls } from '../components/common';

export default function Admin(){
  const {user,requireLogin,notify}=useStore();
  const [tab,setTab]=useState('Juegos'),[games,setGames]=useState<Game[]>([]),[stores,setStores]=useState<TiendaAPI[]>([]),[query,setQuery]=useState(''),[gid,setGid]=useState('');
  const [game,setGame]=useState<Game|null>(null);
  const [logs,setLogs]=useState<{_id:string;accion:string;recurso:string;fecha:string}[]>([]),[error,setError]=useState(''),[reload,setReload]=useState(0);
  useEffect(()=>{if(user?.rol!=='admin')return;let live=true;Promise.all([obtenerCatalogoAdmin(query),obtenerTiendas(true)]).then(([p,t])=>{if(live){setGames(p.items);setStores(t);}}).catch(e=>{if(live)setError(errorMessage(e));});return()=>{live=false;};},[user?.rol,query,reload]);
  useEffect(()=>{setGame(null);if(!gid||tab!=='Ofertas'||user?.rol!=='admin')return;const c=new AbortController();obtenerJuegoAdmin(gid,c.signal).then(setGame).catch(e=>{if(!c.signal.aborted)setError(errorMessage(e));});return()=>c.abort();},[gid,reload,tab,user?.rol]);
  useEffect(()=>{if(tab!=='Registros'||user?.rol!=='admin')return;let live=true;request<typeof logs>('/admin/registros').then(v=>{if(live)setLogs(v);}).catch(e=>{if(live)setError(errorMessage(e));});return()=>{live=false;};},[tab,user?.rol,reload]);
  if(!user)return <main id="main" className="mx-auto max-w-3xl px-4 py-10"><Empty title="Administración" text="Inicia sesión con una cuenta autorizada." action={()=>requireLogin('Se requiere una cuenta con permisos administrativos.')} label="Iniciar sesión"/></main>;
  if(user.rol!=='admin')return <main id="main" className="mx-auto max-w-3xl px-4 py-10"><ErrorState message="No tienes permisos para acceder a Administración."/></main>;
  function selectGame(id:string){setGid(id);}
  const selector=<div className={panel}><label className="block text-sm">Buscar juegos<input value={query} onChange={e=>{setQuery(e.target.value);selectGame('');}} maxLength={150} className={fieldCls}/></label><label className="mt-4 block text-sm">Juego<select value={gid} onChange={e=>selectGame(e.target.value)} className={fieldCls}><option value="">{tab==='Juegos'?'Crear un juego nuevo':'Selecciona un juego'}</option>{games.map(g=><option key={g.id} value={g.id}>{g.title}{g.active===false?" (oculto)":""}</option>)}</select></label><p className="mt-2 text-xs text-slate-400">Se muestran hasta 24 coincidencias. Usa el buscador para encontrar otro juego.</p></div>;
  return <main id="main" className="mx-auto max-w-5xl px-4 py-6"><h1 className="text-2xl font-black">Administración de GameFinder</h1><nav aria-label="Secciones de administración" className="my-5 flex flex-wrap gap-3">{['Juegos','Tiendas','Ofertas','Registros'].map(t=><button key={t} onClick={()=>{setTab(t);setError('');}} className={`rounded-lg px-4 py-3 text-sm ${tab===t?'bg-blue-600 text-white':'border border-blue-500/30'}`}>{t}</button>)}</nav>{error&&<ErrorState message={error} retry={()=>setReload(n=>n+1)}/>}
    {(tab==='Juegos'||tab==='Ofertas')&&selector}
    {tab==='Juegos'&&<GameEditor key={gid||'new'} gameId={gid||undefined} onSaved={()=>{notify('Juego guardado');setReload(n=>n+1);}}/>}
    {tab==='Tiendas'&&<StoreEditor stores={stores} onSaved={()=>{notify('Tienda guardada');setReload(n=>n+1);}}/>}
    {tab==='Ofertas'&&gid&&!game&&!error&&<p aria-live="polite" className="mt-5 text-sm text-slate-400">Cargando ofertas…</p>}
    {tab==='Ofertas'&&game&&<OfferEditor key={`${game.id}-${reload}`} game={game} stores={stores} onSaved={()=>{setGame(null);notify('Oferta guardada');setReload(n=>n+1);}}/>}
    {tab==='Registros'&&<section className={panel}><h2 className="mb-4 font-bold">Últimas 50 operaciones administrativas</h2>{logs.length?logs.map(l=><p key={l._id} className="border-b border-blue-500/20 py-3 text-sm"><b>{l.accion}</b><span className="ml-3 text-slate-400">{dateLabel(l.fecha)}</span><code className="mt-1 block break-all text-xs text-slate-400">{l.recurso}</code></p>):<p className="text-sm text-slate-400">No hay registros administrativos.</p>}</section>}
  </main>;
}
