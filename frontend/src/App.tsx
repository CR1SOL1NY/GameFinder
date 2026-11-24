import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { type Game } from './games';
import { obtenerCatalogo } from './api';
import { miPerfil, guardarDeseado, quitarDeseado, cerrarSesion, type Usuario } from './authApi';
import { ApiError, errorMessage, setSessionExpiredHandler } from './services/http';
import { StoreContext, CatalogContext, type View, type Section } from './context/Store';
import { pathFor, useRoute } from './context/router';
import { Header, MobileNav } from './components/Navigation';
import { Empty, ErrorState, Loading } from './components/Status';
import LoginModal from './components/LoginModal';
import Home from './views/Home';
import { recordComparison } from './services/comparisons';
const Catalog=lazy(()=>import('./views/Catalog'));
const GameDetail=lazy(()=>import('./views/GameDetail'));
const Profile=lazy(()=>import('./views/Profile'));
const Admin=lazy(()=>import('./views/Admin'));

export default function App() {
  const route=useRoute();
  const catalogReturn=useRef('/catalogo');
  useEffect(()=>{if(route.view==='results'||route.view==='offers')catalogReturn.current=location.pathname+location.search;},[route.view,route.search.toString()]);
  const [query,setQuery]=useState(route.search.get('q')||'');
  const [user,setUser]=useState<Usuario|null>(null),[checkingSession,setCheckingSession]=useState(true);
  const userRef=useRef<Usuario|null>(null);userRef.current=user;
  const [games,setGames]=useState<Game[]>([]),[catalogError,setCatalogError]=useState(''),[loadingCatalog,setLoadingCatalog]=useState(true),[reload,setReload]=useState(0);
  const [toast,setToast]=useState(''),[pendingWish,setPendingWish]=useState<string[]>([]);
  const pending=useRef(new Set<string>());
  const [auth,setAuth]=useState<{reason:string;then?:(u:Usuario)=>void|Promise<void>}|null>(null);
  const closeAuth=useCallback(()=>setAuth(null),[]);
  const [theme,setTheme]=useState<'dark'|'light'>(()=>{try{return localStorage.getItem('gf-theme')==='light'?'light':'dark';}catch{return 'dark';}});
  useEffect(()=>{document.documentElement.dataset.theme=theme;try{localStorage.setItem('gf-theme',theme);}catch{/* Navegación privada sin almacenamiento */}},[theme]);
  useEffect(()=>{setQuery(route.search.get('q')||'');},[route.search.toString()]);
  useEffect(()=>{window.scrollTo(0,0);const titles:Record<View,string>={home:'Descubre y compara videojuegos',results:'Catálogo',offers:'Ofertas',detail:'Ficha del videojuego',profile:'Mi cuenta',admin:'Administración',notfound:'Página no encontrada'};document.title=`${titles[route.view]} · GameFinder`;},[route.view,route.gameId,route.section]);
  useEffect(()=>{if(!toast)return;const t=setTimeout(()=>setToast(''),5500);return()=>clearTimeout(t);},[toast]);
  useEffect(()=>{setSessionExpiredHandler(()=>{setUser(null);setToast('Tu sesión expiró. Inicia sesión nuevamente.');});const c=new AbortController();miPerfil(c.signal).then(setUser).catch(e=>{if(!c.signal.aborted&&!(e instanceof ApiError&&e.status===401))setToast(errorMessage(e));}).finally(()=>{if(!c.signal.aborted)setCheckingSession(false);});return()=>{c.abort();setSessionExpiredHandler(()=>{});};},[]);
  useEffect(()=>{if(route.view!=='home')return;const c=new AbortController();setLoadingCatalog(true);setCatalogError('');obtenerCatalogo({sort:'fecha'},c.signal).then(p=>setGames(p.items)).catch(e=>{if(!c.signal.aborted)setCatalogError(errorMessage(e));}).finally(()=>{if(!c.signal.aborted)setLoadingCatalog(false);});return()=>c.abort();},[route.view,reload]);
  const go=(view:View,section?:Section)=>route.navigate(pathFor(view,section));
  const openGame=(id:string)=>route.navigate(`/juegos/${encodeURIComponent(id)}`);
  function compareGame(game:Game){
    if(user&&!recordComparison(user._id,game.id))setToast('Abrimos el comparador, pero no pudimos guardar la actividad en este navegador.');
    openGame(game.id);
  }
  function requireLogin(reason:string,then?:(u:Usuario)=>void|Promise<void>){if(user)void then?.(user);else setAuth({reason,then});}
  async function refreshUser(){try{const next=await miPerfil();if(userRef.current?._id===next._id)setUser(next);}catch(e){if(e instanceof ApiError&&e.status===401){setUser(null);setToast('Tu sesión expiró. Inicia sesión nuevamente.');}throw e;}}
  async function mutateWish(actual:Usuario,game:Game){
    if(pending.current.has(game.id))return;pending.current.add(game.id);setPendingWish([...pending.current]);
    const has=(actual.listaDeseados||[]).some(d=>d.juegoId===game.id);
    try{await(has?quitarDeseado(actual._id,game.id):guardarDeseado(actual._id,game.id));if(userRef.current?._id===actual._id){setUser(prev=>prev?{...prev,listaDeseados:has?(prev.listaDeseados||[]).filter(d=>d.juegoId!==game.id):[...(prev.listaDeseados||[]).filter(d=>d.juegoId!==game.id),{juegoId:game.id,fechaAgregado:new Date().toISOString()}]}:prev);setToast(has?'Juego quitado de tu lista':'Juego guardado en tu lista');}}catch(e){setToast(errorMessage(e));}finally{pending.current.delete(game.id);setPendingWish([...pending.current]);}
  }
  async function toggleWish(game:Game){if(!user){setAuth({reason:'Inicia sesión para guardar este juego en tu lista de deseos.',then:async actual=>{await mutateWish(actual,game);}});return;}await mutateWish(user,game);}
  async function clearWish(){if(!user)return;const results=await Promise.allSettled((user.listaDeseados||[]).map(d=>quitarDeseado(user._id,d.juegoId)));try{await refreshUser();setToast(results.some(r=>r.status==='rejected')?'Algunos juegos no pudieron quitarse. La lista muestra el estado actualizado.':'Lista de deseos vaciada');}catch(e){setToast(errorMessage(e));}}
  async function logout(){try{await cerrarSesion();setUser(null);setToast('Sesión cerrada');go('profile');}catch(e){if(e instanceof ApiError&&e.status===401)setUser(null);else setToast(errorMessage(e));}}
  async function confirmLogin(actual:Usuario){setUser(actual);userRef.current=actual;const next=auth?.then;setAuth(null);setToast('Sesión iniciada correctamente');if(next)await next(actual);}
  const wishlist=user?.listaDeseados?.map(d=>d.juegoId)||[];
  return <StoreContext.Provider value={{user,wishlist,pendingWish,toggleWish,clearWish,openGame,compareGame,notify:setToast,requireLogin,refreshUser,setUser,logout}}><CatalogContext.Provider value={games}>
    <div className="min-h-screen bg-app pb-24 text-fg md:pb-0"><a href="#main" className="skip-link">Saltar al contenido</a><Header view={route.view} section={route.section} query={query} setQuery={setQuery} onSearch={()=>route.navigate(`/catalogo${query.trim()?`?q=${encodeURIComponent(query.trim())}`:''}`)} go={go} loggedIn={!!user} name={user?.nombre||''} wishCount={wishlist.length}/><MobileNav view={route.view} section={route.section} go={go} wishCount={wishlist.length}/>
      <Suspense fallback={<Loading/>}>
        {route.view==='home'&&(loadingCatalog?<Loading text="Cargando videojuegos…"/>:catalogError?<main id="main" className="mx-auto max-w-3xl px-4 py-8"><ErrorState message={catalogError} retry={()=>setReload(n=>n+1)}/></main>:games.length?<div id="main"><Home openResults={()=>go('results')} openOffers={()=>go('offers')}/></div>:<main id="main" className="mx-auto max-w-3xl px-4 py-8"><Empty title="El catálogo está vacío" text="Todavía no hay videojuegos disponibles." action={()=>setReload(n=>n+1)} label="Volver a consultar"/></main>)}
        {(route.view==='results'||route.view==='offers')&&<Catalog search={route.search} navigate={route.navigate} priced={route.view==='offers'}/>}
        {route.view==='detail'&&<GameDetail key={route.gameId} id={route.gameId} back={()=>route.navigate(catalogReturn.current)}/>}
        {route.view==='profile'&&(checkingSession?<Loading text="Comprobando tu sesión…"/>:<Profile key={user?._id||'guest'} section={route.section} setSection={s=>go('profile',s)} openResults={()=>go('results')} theme={theme} setTheme={setTheme} openAdmin={()=>go('admin')}/>)}
        {route.view==='admin'&&(checkingSession?<Loading/>:<Admin/>)}
        {route.view==='notfound'&&<main id="main" className="mx-auto max-w-3xl px-4 py-10"><Empty title="404 · Página no encontrada" text="La dirección no corresponde a una página de GameFinder." action={()=>go('home')} label="Volver al inicio"/></main>}
      </Suspense>
      <footer className="mt-10 border-t border-blue-500/20 px-4 py-8 text-center text-xs leading-6 text-slate-400"><b className="text-white">GameFinder</b> · Descubre, compara y juega.<br/>Precios informados por cada tienda. Confirma plataforma, región y disponibilidad antes de comprar.<div className="mt-3 flex justify-center gap-5"><button onClick={()=>go('results')} className="text-blue-400">Catálogo</button><button onClick={()=>go('profile')} className="text-blue-400">Mi cuenta</button></div></footer>
      {auth&&<LoginModal reason={auth.reason} onConfirm={u=>{void confirmLogin(u);}} onClose={closeAuth}/>}
      <div role="status" aria-live="polite" className={`pointer-events-none fixed bottom-24 left-1/2 z-[75] w-[min(90vw,600px)] -translate-x-1/2 rounded-xl border border-blue-400/40 bg-blue-600 px-5 py-3 text-center text-sm font-semibold text-white shadow-xl md:bottom-6 ${toast?'opacity-100':'opacity-0'}`}>{toast}</div>
    </div>
  </CatalogContext.Provider></StoreContext.Provider>;
}
