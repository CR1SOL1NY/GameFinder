import { useState } from 'react';
import { useCatalog, useStore } from '../context/Store';
import { Img, Icon, type IconName } from '../components/common';
import { GameCard, WishButton } from '../components/GameCard';
import { money, heroOf, coverOf, posterOf } from '../games';
export default function Home({ openResults, openOffers }: { openResults: () => void; openOffers: () => void }) {
  const games = useCatalog();
  const { openGame, compareGame } = useStore();
  const [featureIndex, setFeatureIndex] = useState(0);
  const featured = games[featureIndex % games.length] ?? games[0];
  const feature = { eyebrow: 'Catálogo GameFinder', title: featured.genres.slice(0, 2).join(' · '), copy: featured.description };
  const featuredOffers = [...games]
    .filter((game) => game.price !== null)
    .sort((a, b) => (a.price ?? Infinity) - (b.price ?? Infinity))
    .slice(0, 4);
  const recent = games.filter(g => g.releaseDate && Date.parse(g.releaseDate) <= Date.now()).slice(0, 4);
  const popular = [...games].filter(g => g.reviews > 0).sort((a,b) => b.reviews - a.reviews).slice(0, 4);
  const trending = [...games].sort((a, b) => b.reviews - a.reviews).slice(0, 4);

  const moveFeature = (direction: number) => {
    setFeatureIndex((current) => (current + direction + Math.min(4, games.length)) % Math.min(4, games.length));
  };

  return (
    <>
      <section className="cinematic-hero relative overflow-hidden border-b border-blue-500/30 text-white">
        <Img key={featured.id} src={heroOf(featured)} fallback={coverOf(featured)} alt="" className="home-hero-image absolute inset-0 size-full object-cover object-center" />
        <div className="home-hero-overlay absolute inset-0" />
        <div className="relative mx-auto flex min-h-[540px] max-w-[1500px] items-center justify-center px-5 pb-24 pt-10 text-center sm:min-h-[460px] sm:justify-start sm:px-8 sm:pb-20 sm:text-left lg:px-20">
          <div className="max-w-xl">
            <span className="inline-flex items-center gap-2 rounded-full border border-blue-300/30 bg-blue-600/90 px-3 py-1 text-[9px] font-black uppercase tracking-[0.18em] text-white">
              <span className="size-1.5 rounded-full bg-cyan-300" />{feature.eyebrow}
            </span>
            <p className="mt-5 text-xs font-bold uppercase tracking-[0.22em] text-blue-400">{featured.developer}</p>
            <h1 className="mt-1 text-4xl font-black tracking-tight sm:text-6xl">{featured.title}</h1>
            <h2 className="mt-1 text-xl font-extrabold text-blue-400 sm:text-3xl">{feature.title}</h2>
            <p className="mt-4 max-w-lg text-xs leading-5 text-slate-300 sm:text-sm sm:leading-6">{feature.copy}</p>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-3 sm:justify-start">
              <button onClick={() => compareGame(featured)} className="flex items-center gap-3 rounded-full bg-blue-600 px-7 py-3 text-xs font-bold text-white shadow-[0_0_28px_rgba(37,99,235,.4)] transition hover:bg-blue-500">Comparar precios <Icon name="arrow" className="size-4" /></button>
              <WishButton game={featured} className="!size-11 !border !border-white/20 !bg-black/50" />
              <div className="ml-1">
                <span className="block text-[9px] uppercase tracking-wider text-slate-400">Mejor precio</span>
                <b className="text-lg">{money(featured.price)}</b>
              </div>
            </div>
          </div>
          <div className="absolute bottom-6 left-1/2 flex -translate-x-1/2 items-center gap-2 sm:bottom-8 sm:left-auto sm:right-8 sm:translate-x-0 lg:right-20">
            <button onClick={() => moveFeature(-1)} aria-label="Destacado anterior" className="grid size-9 place-items-center rounded-full border border-white/20 bg-black/40 text-white backdrop-blur transition hover:bg-blue-600"><Icon name="arrow" className="size-4 rotate-180" /></button>
            <div className="flex gap-1.5 rounded-full border border-white/10 bg-black/35 px-3 py-2 backdrop-blur">
              {games.slice(0, 4).map((item, index) => <button key={item.id} onClick={() => setFeatureIndex(index)} aria-label={`Mostrar ${item.title}`} className={`h-1.5 rounded-full transition-all ${index === featureIndex ? 'w-6 bg-blue-400' : 'w-1.5 bg-white/50 hover:bg-white'}`} />)}
            </div>
            <button onClick={() => moveFeature(1)} aria-label="Siguiente destacado" className="grid size-9 place-items-center rounded-full border border-white/20 bg-black/40 text-white backdrop-blur transition hover:bg-blue-600"><Icon name="arrow" className="size-4" /></button>
          </div>
        </div>
      </section>
      <div className="mx-auto max-w-[1500px] px-4 py-5 lg:px-8">
        <div className="grid overflow-hidden rounded-2xl border border-blue-500/20 bg-panel shadow-xl shadow-blue-950/5 sm:grid-cols-2 lg:grid-cols-4">
          {[['search', 'Precios registrados', 'Ofertas registradas en la base de datos.'], ['tag', 'Compara tiendas', 'Consulta precios informados por tiendas.'], ['shield', 'Tiendas disponibles', 'Revisa cada tienda antes de comprar.'], ['star', 'Recomendaciones', 'Juegos para ti.']].map(([icon, title, text]) => <div key={title} className="flex items-center justify-center gap-3 border-b border-blue-500/15 p-4 text-center sm:justify-start sm:border-r sm:text-left lg:border-b-0"><span className="grid size-10 place-items-center rounded-full bg-blue-500/15 text-blue-400"><Icon name={icon as IconName} /></span><div><p className="text-xs font-bold">{title}</p><p className="mt-0.5 text-[9px] text-slate-500">{text}</p></div></div>)}
        </div>

        <section className="mt-10">
          <div className="mb-4 flex flex-col items-center gap-3 text-center sm:flex-row sm:items-end sm:justify-between sm:text-left">
            <div><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-blue-400">Ahorra más, juega más</p><h2 className="mt-1 text-xl font-black sm:text-2xl">Precios disponibles</h2></div>
            <button onClick={openOffers} className="flex shrink-0 items-center gap-2 text-[11px] font-bold text-blue-400 hover:text-blue-300">Ver todas <Icon name="arrow" className="size-3.5" /></button>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {featuredOffers.length ? featuredOffers.map((game) => <GameCard key={game.id} game={game} />) : <p className="text-xs text-slate-400">No hay precios CLP registrados por ahora.</p>}
          </div>
        </section>

        <section className="mt-10 grid gap-4 lg:grid-cols-[1.35fr_1fr]">
          <div className="relative overflow-hidden rounded-2xl border border-blue-400/30 bg-blue-600 p-6 text-center text-white sm:p-8 sm:text-left">
            <div className="promo-grid absolute inset-0 opacity-50" />
            <div className="relative max-w-md">
              <span className="mx-auto grid size-11 place-items-center rounded-xl bg-white/15 sm:mx-0"><Icon name="bell" /></span>
              <p className="mt-5 text-[10px] font-bold uppercase tracking-[0.2em] text-blue-100">Una función de GameFinder</p>
              <h2 className="mt-2 text-2xl font-black sm:text-3xl">Que el precio baje, no tus ganas de jugar</h2>
              <p className="mt-3 text-xs leading-5 text-blue-100">Guarda tus favoritos y revisa sus mejores precios desde un solo lugar. Consulta los precios registrados antes de comprar.</p>
              <button onClick={() => openGame((featuredOffers[0] ?? featured).id)} className="mx-auto mt-6 flex min-h-11 items-center gap-2 rounded-full bg-white px-5 py-2.5 text-xs font-extrabold text-blue-700 transition hover:bg-blue-50 sm:mx-0">{featuredOffers.length ? 'Explorar una oferta' : 'Ver videojuego'} <Icon name="arrow" className="size-4" /></button>
            </div>
            <Img src={posterOf(featuredOffers[0] ?? featured)} fallback={coverOf(featuredOffers[0] ?? featured)} alt="" className="absolute -bottom-16 right-4 hidden h-72 rotate-6 rounded-2xl border-4 border-white/20 object-cover shadow-2xl sm:block" />
          </div>
          <div className="rounded-2xl border border-blue-500/20 bg-panel p-5 sm:p-6">
            <div className="flex items-center justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-blue-400">Ahora mismo</p><h2 className="mt-1 text-lg font-black">Juegos del catálogo</h2></div><span className="rounded-full bg-emerald-500/15 px-2.5 py-1 text-[9px] font-bold text-emerald-400">Catálogo</span></div>
            <div className="mt-4 divide-y divide-blue-500/15">
              {trending.map((game, index) => (
                <button key={game.id} onClick={() => openGame(game.id)} className="group flex w-full items-center gap-3 py-3 text-left">
                  <span className="w-5 text-center text-xs font-black text-slate-500">{String(index + 1).padStart(2, '0')}</span>
                  <Img src={coverOf(game)} fallback={coverOf(game)} alt="" className="aspect-[460/215] w-20 rounded-md bg-black object-cover object-center" />
                  <span className="min-w-0 flex-1"><b className="block truncate text-xs group-hover:text-blue-400">{game.title}</b><span className="text-[9px] text-slate-500">{game.reviews.toLocaleString('es-CL')} calificaciones</span></span>
                  <b className="text-xs">{money(game.price)}</b>
                </button>
              ))}
            </div>
          </div>
        </section>

        {recent.length > 0 && <section className="mt-10"><h2 className="mb-4 text-xl font-black">Lanzamientos recientes del catálogo</h2><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{recent.map(g => <GameCard key={g.id} game={g} />)}</div></section>}
        {popular.length > 1 && <section className="mt-10"><h2 className="mb-4 text-xl font-black">Más calificados de esta selección</h2><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{popular.map(g => <GameCard key={g.id} game={g} />)}</div></section>}

        <section className="mt-10 flex flex-col items-center rounded-2xl border border-blue-500/25 bg-panel px-6 py-12 text-center">
          <span className="grid size-14 place-items-center rounded-2xl bg-blue-600/20 text-blue-400"><Icon name="grid" className="size-7" /></span>
          <h2 className="mt-5 text-2xl font-black">Tu próxima aventura empieza aquí</h2>
          <p className="mt-2 max-w-lg text-xs leading-5 text-slate-400">Explora el catálogo, filtra por género, plataforma y precio, y compara entre las tiendas registradas.</p>
          <button onClick={openResults} className="mt-6 flex items-center gap-3 rounded-full bg-blue-600 px-8 py-3.5 text-xs font-bold text-white shadow-[0_0_24px_rgba(37,99,235,.4)] hover:bg-blue-500">Explorar catálogo <Icon name="arrow" className="size-4" /></button>
        </section>
      </div>
    </>
  );
}

