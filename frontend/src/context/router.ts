import { useEffect, useState } from 'react';
import type { View, Section } from './Store';
const sections: Record<string, Section> = { '': 'Mi perfil', deseados: 'Lista de deseados', calificaciones: 'Mis calificaciones', configuracion: 'Configuración', comparados: 'Juegos comparados' };
export function readRoute() {
  const path = window.location.pathname.replace(/\/$/, '') || '/';
  const search = new URLSearchParams(window.location.search);
  let view: View = 'notfound', section: Section = 'Mi perfil', gameId = '';
  if (path === '/') view = 'home';
  if (path === '/catalogo') view = 'results';
  if (path === '/ofertas') view = 'offers';
  if (path === '/admin') view = 'admin';
  const detail = path.match(/^\/juegos\/([^/]+)$/);
  if (detail) { view = 'detail'; try { gameId = decodeURIComponent(detail[1]); } catch { view = 'notfound'; } }
  if (path === '/perfil' || path.startsWith('/perfil/')) { const part = path.split('/')[2] || ''; if (part in sections) {view = 'profile'; section = sections[part];} }
  return {view, section, gameId, search};
}
export function useRoute() {
  const [route, setRoute] = useState(readRoute);
  useEffect(() => { const onPop = () => setRoute(readRoute()); window.addEventListener('popstate', onPop); return () => window.removeEventListener('popstate', onPop); }, []);
  function navigate(path: string, replace = false) { if (replace) history.replaceState(null, '', path); else history.pushState(null, '', path); setRoute(readRoute()); }
  return { ...route, navigate };
}
export function pathFor(view: View, section: Section = 'Mi perfil') {
  if (view === 'home') return '/';
  if (view === 'results') return '/catalogo';
  if (view === 'offers') return '/ofertas';
  if (view === 'admin') return '/admin';
  if (view === 'profile') return '/perfil' + ({'Mi perfil': '', 'Lista de deseados': '/deseados', 'Mis calificaciones': '/calificaciones', 'Configuración': '/configuracion', 'Juegos comparados': '/comparados'}[section]);
  return '/404';
}
