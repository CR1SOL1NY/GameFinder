import { useEffect, useState } from 'react';
import { useStore, type Section } from '../../context/Store';
import { recomendaciones } from '../../authApi';
import { reviewSummary, type ReviewSummary } from '../../services/reviews';
import { useComparisonHistory } from '../../services/comparisons';
import { useProfileGames } from '../../hooks/useProfileGames';
import { errorMessage } from '../../services/http';
import { coverOf, dateLabel, money, safeUrl, type Game } from '../../games';
import { Img, Icon, panel, type IconName } from '../common';
import { Empty, ErrorState } from '../Status';
import { GameCard, WishButton } from '../GameCard';
import ReviewCard from './ReviewCard';
import { ComparisonList, historyNote } from './ComparisonHistory';

function Recommendations({ edit }: { edit: () => void }) {
  const { user } = useStore();
  const [games, setGames] = useState<Game[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    recomendaciones(user!._id, controller.signal).then(setGames).catch(err => { if (!controller.signal.aborted) setError(errorMessage(err)); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [user!._id, retry]);
  return <section aria-labelledby="recommendations-title">
    <h2 id="recommendations-title" className="text-base font-bold">Recomendaciones para ti</h2>
    <p className="mb-4 mt-2 text-xs leading-5 text-slate-400">Según tus géneros, plataformas y presupuesto CLP.</p>
    {loading ? <p className="text-sm text-slate-400">Cargando recomendaciones…</p> : error ? <ErrorState message={error} retry={() => setRetry(n => n + 1)} /> : games.length ? <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{games.slice(0, 3).map(game => <GameCard key={game.id} game={game} />)}</div> : <Empty title="Sin coincidencias por ahora" text="Amplía tu presupuesto o ajusta tus preferencias." action={edit} label="Editar preferencias" />}
  </section>;
}

export default function ProfileOverview({ setSection }: { setSection: (section: Section) => void }) {
  const { user, wishlist, openGame, compareGame } = useStore();
  const { entries, available } = useComparisonHistory(user!._id);
  const recent = entries.slice(0, 3);
  const desired = [...(user!.listaDeseados || [])].sort((a, b) => (Date.parse(b.fechaAgregado) || 0) - (Date.parse(a.fechaAgregado) || 0)).slice(0, 3);
  const data = useProfileGames([...recent.map(row => row.gameId), ...desired.map(row => row.juegoId)]);
  const [summary, setSummary] = useState<ReviewSummary | null>(null);
  const [reviewError, setReviewError] = useState('');
  const [loadingReviews, setLoadingReviews] = useState(true);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setSummary(null); setLoadingReviews(true); setReviewError('');
    reviewSummary(controller.signal).then(setSummary).catch(err => { if (!controller.signal.aborted) setReviewError(errorMessage(err)); }).finally(() => { if (!controller.signal.aborted) setLoadingReviews(false); });
    return () => controller.abort();
  }, [user!._id, retry]);
  const prefs = user!.preferencias;
  const banner = [...data.games.values()].find(game => game.imageUrl)?.imageUrl || safeUrl(summary?.ultimas.find(review => review.juego?.imagenPortada)?.juego?.imagenPortada);
  const stats: { icon: IconName; value: string; title: string; detail?: string; section: Section }[] = [
    { icon: 'heart', value: String(new Set(wishlist).size), title: 'Juegos en tu lista de deseados', section: 'Lista de deseados' },
    { icon: 'monitor', value: available ? String(entries.length) : '—', title: 'Juegos comparados', detail: 'En este navegador', section: 'Juegos comparados' },
    { icon: 'star', value: loadingReviews ? '…' : summary?.promedio != null ? summary.promedio.toLocaleString('es-CL', { maximumFractionDigits: 1, minimumFractionDigits: 1 }) : '—', title: 'Promedio de mis reseñas', detail: summary ? `${summary.total} ${summary.total === 1 ? 'reseña' : 'reseñas'} · escala de 0,5 a 5` : reviewError ? 'No disponible' : 'Sin reseñas todavía', section: 'Mis calificaciones' },
  ];
  return <div className="space-y-5">
    <section className="profile-banner relative isolate overflow-hidden rounded-2xl border border-blue-500/30 text-white">
      {banner && <Img src={banner} fallback="/cover-placeholder.svg" alt="" className="pointer-events-none absolute inset-0 -z-20 size-full object-cover object-center opacity-50" />}
      <div className="profile-banner-shade pointer-events-none absolute inset-0 -z-10" />
      <div className="flex flex-col gap-6 p-5 sm:p-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-center gap-4">
          <span className="grid size-18 shrink-0 place-items-center rounded-full border-2 border-blue-500 bg-[#111827]/80 text-blue-300 shadow-lg shadow-blue-500/15"><Icon name="user" className="size-9" /></span>
          <div className="min-w-0"><h1 className="break-words text-2xl font-extrabold">{user!.nombre}</h1><p className="mt-1 break-all text-xs text-white/85">{user!.correo}</p><p className="mt-1 text-xs text-white/65">Miembro desde {dateLabel(user!.fechaRegistro)}</p><button onClick={() => setSection('Configuración')} className="mt-3 rounded-lg bg-blue-600 px-4 py-2.5 text-xs font-bold text-white hover:bg-blue-500">Editar perfil y preferencias</button></div>
        </div>
        <div className="grid min-w-0 grid-cols-3 gap-2 lg:w-[48%]" role="group" aria-label="Estadísticas de tu perfil">
          {stats.map(stat => <button key={stat.title} onClick={() => setSection(stat.section)} className="min-w-0 rounded-xl border border-white/15 bg-[#111827]/75 p-3 text-left transition hover:border-blue-400 hover:bg-[#172033]/90"><Icon name={stat.icon} className="size-4 text-blue-400" /><span className="mt-2 block text-xl font-extrabold sm:text-2xl">{stat.value}</span><span className="mt-1 block break-words text-[10px] leading-4 text-white/85 sm:text-[11px]">{stat.title}</span>{stat.detail && <span className="mt-1 block text-[10px] leading-4 text-white/60">{stat.detail}</span>}</button>)}
        </div>
      </div>
    </section>

    <div className="grid gap-5 lg:grid-cols-2">
      <section aria-labelledby="preferences-title" className={panel}>
        <div className="flex items-center justify-between gap-3"><h2 id="preferences-title" className="text-sm font-bold">Mis preferencias</h2><button onClick={() => setSection('Configuración')} aria-label="Editar mis preferencias" className="inline-flex min-h-10 items-center gap-2 text-xs font-bold text-blue-400">Editar <Icon name="arrow" className="size-3.5" /></button></div>
        <dl className="mt-3 grid grid-cols-2 gap-x-5 gap-y-5 text-sm">
          <div className="col-span-2"><dt className="text-xs text-slate-400">Plataformas favoritas</dt><dd className="mt-1 font-semibold">{prefs?.plataformas?.join(' · ') || 'Sin definir'}</dd></div>
          <div><dt className="text-xs text-slate-400">Presupuesto mínimo</dt><dd className="mt-1 font-bold">{prefs ? money(prefs.precioMin) : 'Sin definir'}</dd></div>
          <div><dt className="text-xs text-slate-400">Presupuesto máximo</dt><dd className="mt-1 font-bold">{prefs ? money(prefs.precioMax) : 'Sin definir'}</dd></div>
        </dl>
        <h3 className="mb-3 mt-6 text-xs font-bold">Géneros que te interesan</h3>
        {prefs?.generos?.length ? <ul className="flex flex-wrap gap-2">{prefs.generos.map(genre => <li key={genre} className="rounded-md border border-blue-500/30 bg-field px-3 py-1.5 text-xs font-semibold">{genre}</li>)}</ul> : <p className="text-xs leading-5 text-slate-400">Elige tus géneros en Editar para personalizar tus recomendaciones.</p>}
      </section>
      <section aria-labelledby="activity-title" className={panel}>
        <div className="mb-3 flex items-center justify-between gap-3"><h2 id="activity-title" className="text-sm font-bold">Tu actividad reciente</h2>{entries.length > 3 && <button onClick={() => setSection('Juegos comparados')} className="min-h-10 text-xs font-bold text-blue-400">Ver todos los juegos comparados →</button>}</div>
        {!available ? <p className="py-4 text-sm text-rose-300">El historial no está disponible en este navegador.</p> : !recent.length ? <div className="rounded-xl border border-dashed border-blue-500/25 px-5 py-7 text-center"><Icon name="monitor" className="mx-auto size-7 text-blue-400" /><p className="mt-3 text-sm font-bold">Tu próxima comparación aparecerá aquí</p><p className="mt-2 text-xs leading-5 text-slate-400">Pulsa Comparar precios en un juego para registrar tu actividad.</p></div> : data.loading ? <p className="py-8 text-sm text-slate-400">Cargando actividad…</p> : data.error ? <ErrorState message={data.error} retry={data.retry} /> : <ComparisonList entries={recent} games={data.games} />}
        <p className="mt-4 text-[11px] leading-5 text-slate-400">{historyNote}</p>
      </section>
    </div>

    <section aria-labelledby="wishlist-preview-title">
      <div className="mb-3 flex items-center justify-between gap-3"><h2 id="wishlist-preview-title" className="text-sm font-bold">Tu lista de deseados ({new Set(wishlist).size})</h2>{wishlist.length > 0 && <button onClick={() => setSection('Lista de deseados')} className="min-h-10 text-xs font-bold text-blue-400">Ver toda la lista →</button>}</div>
      {!desired.length ? <div className="rounded-xl border border-dashed border-blue-500/30 px-5 py-7 text-center text-xs leading-5 text-slate-400">Aún no has añadido juegos. Toca el corazón de cualquier juego para guardarlo aquí.</div> : data.loading ? <p className="text-sm text-slate-400">Cargando tus juegos…</p> : data.error ? <ErrorState message={data.error} retry={data.retry} /> : <div className="grid gap-3 md:grid-cols-3">{desired.map(item => {
        const game = data.games.get(item.juegoId);
        return game ? <article key={item.juegoId} className="relative flex min-w-0 gap-3 rounded-xl border border-blue-500/25 bg-panel p-3"><button onClick={() => openGame(game.id)} aria-label={`Ver ${game.title}`} className="shrink-0"><Img src={coverOf(game)} fallback="/cover-placeholder.svg" alt="" className="h-20 w-16 rounded-lg object-cover" /></button><div className="min-w-0 pr-6"><h3 className="break-words text-xs font-bold">{game.title}</h3><p className="mt-2 text-[11px] text-slate-400">{game.price === null ? 'Precio no disponible' : `Desde ${money(game.price)}`}</p><button onClick={() => compareGame(game)} className="mt-2 py-1 text-xs font-bold text-blue-400">Comparar precios →</button></div><WishButton game={game} className="absolute right-2 top-2" /></article> : <p key={item.juegoId} className={`${panel} text-xs text-slate-400`}>Un juego de tu lista ya no está disponible en el catálogo.</p>;
      })}</div>}
    </section>

    <section aria-labelledby="recent-reviews-title" className={panel}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><h2 id="recent-reviews-title" className="text-sm font-bold">Últimas reseñas</h2>{summary && summary.total > 3 && <button onClick={() => setSection('Mis calificaciones')} className="min-h-10 text-xs font-bold text-blue-400">Ver todas las reseñas ({summary.total}) →</button>}</div>
      {loadingReviews ? <p className="py-6 text-sm text-slate-400">Cargando tus reseñas…</p> : reviewError ? <ErrorState message={reviewError} retry={() => setRetry(n => n + 1)} /> : summary?.ultimas.length ? <div className="grid gap-3 md:grid-cols-3">{summary.ultimas.map(review => <ReviewCard key={review._id} review={review} compact />)}</div> : <p className="rounded-lg border border-dashed border-blue-500/25 p-6 text-center text-sm text-slate-400">Todavía no has publicado reseñas. Califica un juego desde su ficha.</p>}
    </section>
    <Recommendations edit={() => setSection('Configuración')} />
  </div>;
}
