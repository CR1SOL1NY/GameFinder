import { useEffect, useId, useState } from 'react';
import { obtenerCatalogo, obtenerJuego } from '../api';
import { coverOf, dateLabel, money, type Game } from '../games';
import { errorMessage } from '../services/http';
import { Img, Icon } from '../components/common';
import { WishButton, GameCard } from '../components/GameCard';
import { Loading, ErrorState } from '../components/Status';
import OfferComparison from '../components/OfferComparison';
import GameInformation from '../components/GameInformation';
import Reviews from '../components/Reviews';

const tabs = ['Información', 'Reseñas'] as const;
type Tab = typeof tabs[number];

export default function GameDetail({ id, back }: { id: string; back: () => void }) {
  const [game, setGame] = useState<Game | null>(null), [related, setRelated] = useState<Game[]>([]), [relatedError, setRelatedError] = useState('');
  const [error, setError] = useState(''), [loading, setLoading] = useState(true), [reload, setReload] = useState(0), [tab, setTab] = useState<Tab>('Información');
  const tabId = useId();
  useEffect(() => {
    const controller = new AbortController();
    setGame(null); setLoading(true); setError(''); setTab('Información');
    obtenerJuego(id, controller.signal).then(setGame).catch(err => { if (!controller.signal.aborted) setError(errorMessage(err)); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [id, reload]);
  const genre = game?.genres[0];
  useEffect(() => {
    setRelated([]); setRelatedError('');
    if (!genre) return;
    const controller = new AbortController();
    obtenerCatalogo({ genres: [genre] }, controller.signal).then(page => setRelated(page.items.filter(item => item.id !== id).slice(0, 4))).catch(err => { if (!controller.signal.aborted) setRelatedError(errorMessage(err)); });
    return () => controller.abort();
  }, [genre, id]);
  function showReviews() {
    setTab('Reseñas');
    document.getElementById(`${tabId}-tabs`)?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
  }
  function moveTab(event: React.KeyboardEvent<HTMLButtonElement>) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const next: Tab = event.key === 'Home' ? 'Información' : event.key === 'End' ? 'Reseñas' : tab === 'Información' ? 'Reseñas' : 'Información';
    setTab(next);
    document.getElementById(`${tabId}-${next}`)?.focus();
  }
  if (loading) return <Loading text="Cargando ficha del videojuego…" />;
  if (error || !game) return <main id="main" className="mx-auto max-w-3xl px-4 py-8"><ErrorState message={error || 'Juego no encontrado'} retry={() => setReload(n => n + 1)} /><button onClick={back} className="text-blue-400">Volver al catálogo</button></main>;
  return <main id="main">
    <section className="cinematic-hero relative overflow-hidden border-b border-blue-500/20 bg-[#111827] text-white" aria-label="Presentación del videojuego">
      <Img src={game.backgroundUrl || coverOf(game)} fallback={coverOf(game)} alt="" className="detail-hero-image pointer-events-none absolute inset-0 size-full object-cover" />
      <div className="detail-hero-overlay pointer-events-none absolute inset-0" />
      <div className="relative mx-auto grid max-w-[1500px] gap-5 px-4 py-5 text-center sm:grid-cols-[160px_minmax(0,1fr)] sm:gap-6 sm:text-left lg:px-8">
        <Img src={coverOf(game)} fallback="/cover-placeholder.svg" alt={`Portada de ${game.title}`} className="mx-auto aspect-[2/3] w-32 rounded-lg border border-white/15 bg-[#111827] object-cover shadow-xl sm:w-full" />
        <div className="min-w-0 self-center">
          <nav aria-label="Ruta del videojuego" className="mb-2 flex flex-wrap items-center justify-center gap-1 text-[11px] text-blue-400 sm:justify-start"><button onClick={back} className="inline-flex items-center gap-1 py-1 hover:text-white"><Icon name="back" className="size-3" />Volver al catálogo</button><span aria-hidden="true">›</span><span aria-current="page" className="line-clamp-1 text-white/65">{game.title}</span></nav>
          <h1 className="max-w-2xl break-words text-3xl font-extrabold leading-tight tracking-tight sm:text-[34px]">{game.title}</h1>
          {(game.developer || game.releaseDate) && <p className="mt-1 text-[11px] text-white/65">{game.developer}{game.developer && game.year && <span aria-hidden="true"> · </span>}{game.releaseDate && <time dateTime={game.releaseDate} title={`Lanzamiento: ${dateLabel(game.releaseDate, true)}`}>{game.year}</time>}</p>}
          {!!game.genres.length && <ul className="mt-2 flex flex-wrap justify-center gap-1.5 sm:justify-start">{game.genres.map(genre => <li key={genre} className="rounded-md border border-white/10 bg-[#16365C]/80 px-3 py-1 text-[11px] text-white">{genre}</li>)}</ul>}
          <p className="mx-auto mt-3 line-clamp-2 max-w-xl whitespace-pre-line text-xs leading-5 text-white/90 sm:mx-0">{game.summary || game.description}</p>
          <button onClick={showReviews} className="mt-2 inline-flex min-h-8 flex-wrap items-center justify-center gap-2 py-1 text-xs hover:text-blue-300 sm:justify-start"><Icon name="star" filled className="size-3.5 text-yellow-400" />{game.reviews > 0 ? <><b>{game.rating.toLocaleString('es-CL', { maximumFractionDigits: 1 })}</b><span className="text-white/65">({game.reviews.toLocaleString('es-CL')} {game.reviews === 1 ? 'reseña' : 'reseñas'})</span></> : <span className="text-white/65">Sin reseñas todavía · Sé el primero en calificar</span>}</button>
          <div className="mt-2 flex flex-wrap items-center justify-center gap-x-5 gap-y-3 sm:justify-start"><p className="flex flex-wrap items-baseline justify-center gap-2"><span className="text-[11px] text-white/60">Desde · CLP</span><strong className="text-3xl font-extrabold">{money(game.price)}</strong></p><WishButton game={game} variant="label" /></div>
        </div>
      </div>
    </section>
    <div className="mx-auto grid max-w-[1500px] gap-5 px-4 py-5 lg:grid-cols-[minmax(0,1fr)_minmax(340px,36%)] lg:px-8">
      <section className="min-w-0">
        <div id={`${tabId}-tabs`} role="tablist" aria-label="Información del videojuego" className="flex scroll-mt-36 border-b border-blue-500/25">{tabs.map(value => <button key={value} role="tab" id={`${tabId}-${value}`} aria-selected={tab === value} tabIndex={tab === value ? 0 : -1} aria-controls={`${tabId}-panel`} onClick={() => setTab(value)} onKeyDown={moveTab} className={`flex-1 border-b-2 px-4 py-4 text-xs font-semibold transition ${tab === value ? 'border-blue-500 text-blue-400' : 'border-transparent text-slate-400 hover:text-blue-400'}`}>{value}</button>)}</div>
        <div role="tabpanel" id={`${tabId}-panel`} aria-labelledby={`${tabId}-${tab}`} tabIndex={0}>{tab === 'Información' ? <GameInformation game={game} /> : <Reviews gameId={id} changed={() => { void obtenerJuego(id).then(setGame).catch(err => setError(errorMessage(err))); }} />}</div>
      </section>
      <aside className="min-w-0" aria-label="Tiendas y precios del videojuego"><OfferComparison game={game} /></aside>
    </div>
    {!!related.length && <section className="mx-auto max-w-[1500px] px-4 py-6 lg:px-8"><h2 className="mb-4 text-lg font-bold">Juegos relacionados por género</h2><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{related.map(item => <GameCard key={item.id} game={item} />)}</div></section>}
    {relatedError && <p className="mx-auto max-w-[1500px] px-4 text-xs text-slate-400">No pudimos cargar los juegos relacionados.</p>}
  </main>;
}
