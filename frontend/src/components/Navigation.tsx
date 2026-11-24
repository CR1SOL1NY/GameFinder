import { Icon } from './common';
import NotificationBell from './NotificationBell';
import type { View, Section } from '../context/Store';
export function Header({ view, section, query, setQuery, onSearch, go, loggedIn, name, wishCount }: { view: View; section: Section; query: string; setQuery: (s: string) => void; onSearch: () => void; go: (v: View, s?: Section) => void; loggedIn: boolean; name: string; wishCount: number }) {
  const onWish = view === 'profile' && section === 'Lista de deseados';
  const nav = [['home', 'Inicio', 'home'], ['results', 'Catálogo', 'grid']] as const;
  return (
    <header className="sticky top-0 z-50 border-b border-blue-500/20 bg-header/95 backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1500px] flex-wrap items-center gap-2 px-4 py-3 md:h-16 md:flex-nowrap md:gap-4 md:py-0 lg:px-8">
        <button onClick={() => go('home')} className="flex shrink-0 items-center gap-2">
          <span className="grid size-9 place-items-center rounded-xl bg-blue-600 text-white shadow-[0_0_22px_rgba(37,99,235,.45)]"><Icon name="gamepad" /></span>
          <span className="text-lg font-extrabold">Game<span className="text-blue-400">Finder</span></span>
        </button>
        <div className="order-3 mx-auto mt-1 flex w-full items-center rounded-xl border border-blue-500/35 bg-field px-3 focus-within:border-blue-400 md:order-none md:mt-0 md:max-w-2xl md:flex-1">
          <Icon name="search" className="size-4 text-blue-300" />
          <input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && onSearch()} className="h-10 min-w-0 flex-1 bg-transparent px-3 text-xs outline-none placeholder:text-slate-500" aria-label="Buscar juegos" maxLength={150} placeholder="Busca juegos, géneros, plataformas..." />
          <button onClick={onSearch} aria-label="Buscar" className="grid size-10 place-items-center text-blue-300"><Icon name="search" className="size-4" /></button>
        </div>
        <div className="ml-auto flex items-center gap-1">
          <button onClick={() => go('profile', 'Lista de deseados')} className="icon-button relative !hidden md:!grid" aria-label="Lista de deseados">
            <Icon name="heart" filled={wishCount > 0} />
            {wishCount > 0 && <span className="absolute right-0.5 top-0.5 grid min-w-4 place-items-center rounded-full bg-blue-500 px-1 text-[9px] font-bold text-white">{wishCount}</span>}
          </button>
          <NotificationBell />
          <button onClick={() => go('profile', 'Mi perfil')} aria-label="Perfil" className="ml-1 flex min-h-10 items-center gap-2 rounded-full border border-blue-500/30 p-1 pr-2 text-xs sm:pr-3"><span className="grid size-7 place-items-center rounded-full bg-blue-600 text-white"><Icon name="user" className="size-4" /></span><span className="hidden sm:inline">{loggedIn ? name.split(' ')[0] : 'Iniciar sesión'}</span></button>
        </div>
      </div>
      <nav aria-label="Navegación principal" className="mx-auto hidden h-11 max-w-[1500px] items-center gap-1 px-4 md:flex lg:px-8">
        {nav.map(([target, label, icon]) => <button key={label} onClick={() => go(target)} className={`nav-button ${view === target ? 'nav-active' : ''}`}><Icon name={icon} className="size-4" />{label}</button>)}
        <button onClick={() => go('offers')} className={`nav-button ${view === 'offers' ? 'nav-active' : ''}`}><Icon name="tag" className="size-4" />Ofertas</button>
        <button onClick={() => go('profile', 'Lista de deseados')} className={`nav-button ${onWish ? 'nav-active' : ''}`}><Icon name="heart" className="size-4" />Mi lista de deseados{wishCount > 0 && <span className="rounded-full bg-white/20 px-1.5 text-[9px]">{wishCount}</span>}</button>
        <button onClick={() => go('profile', 'Mi perfil')} className={`nav-button ${view === 'profile' && !onWish ? 'nav-active' : ''}`}><Icon name="user" className="size-4" />Mi perfil</button>
      </nav>
    </header>
  );
}

export function MobileNav({ view, section, go, wishCount }: { view: View; section: Section; go: (v: View, s?: Section) => void; wishCount: number }) {
  const onWish = view === 'profile' && section === 'Lista de deseados';
  return (
    <nav aria-label="Navegación principal móvil" className="mobile-bottom-nav fixed inset-x-0 bottom-0 z-[65] grid grid-cols-5 border-t border-blue-500/20 bg-header/95 px-1 pt-1 backdrop-blur-xl md:hidden">
      {([
        ['home', 'Inicio', 'home', () => go('home'), view === 'home'],
        ['results', 'Catálogo', 'grid', () => go('results'), view === 'results'],
        ['offers', 'Ofertas', 'tag', () => go('offers'), view === 'offers'],
        ['wish', 'Deseados', 'heart', () => go('profile', 'Lista de deseados'), onWish],
        ['profile', 'Perfil', 'user', () => go('profile', 'Mi perfil'), view === 'profile' && !onWish],
      ] as const).map(([key, label, icon, action, active]) => (
        <button key={key} onClick={action} className={`relative flex min-h-14 flex-col items-center justify-center gap-1 rounded-lg text-[9px] font-semibold ${active ? 'bg-blue-600/15 text-blue-400' : 'text-slate-400'}`}>
          <Icon name={icon} className="size-5" filled={key === 'wish' && wishCount > 0} />
          {label}
          {key === 'wish' && wishCount > 0 && <span className="absolute right-[22%] top-1 grid min-w-4 place-items-center rounded-full bg-blue-600 px-1 text-[8px] text-white">{wishCount}</span>}
        </button>
      ))}
    </nav>
  );
}

