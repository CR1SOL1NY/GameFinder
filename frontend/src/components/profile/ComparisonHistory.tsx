import { useEffect, useState } from 'react';
import { useStore } from '../../context/Store';
import { useComparisonHistory, type Comparison } from '../../services/comparisons';
import { useProfileGames } from '../../hooks/useProfileGames';
import { type Game, coverOf } from '../../games';
import { Img, Icon, panel } from '../common';
import { Empty, ErrorState } from '../Status';

export const historyNote = 'Actividad guardada en este navegador, separada por cuenta. No se sincroniza con otros dispositivos.';

function comparedDate(value: string) {
  return new Intl.DateTimeFormat('es-CL', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

export function ComparisonList({ entries, games }: { entries: Comparison[]; games: Map<string, Game> }) {
  const { openGame } = useStore();
  return <ul className="space-y-2">{entries.map(entry => {
    const game = games.get(entry.gameId);
    return <li key={entry.gameId}>
      <button disabled={!game} onClick={() => openGame(entry.gameId)} className="group flex w-full items-center gap-3 rounded-lg p-2 text-right transition hover:bg-blue-500/10 disabled:cursor-default">
        <Img src={game ? coverOf(game) : '/cover-placeholder.svg'} fallback="/cover-placeholder.svg" alt="" className="h-12 w-20 shrink-0 rounded-md bg-field object-cover" />
        <span className="ml-auto min-w-0 pl-4 text-right"><span className="block text-xs text-slate-400">Comparaste precios de</span><b className="mt-0.5 block break-words text-sm group-hover:text-blue-400">{game?.title || 'Videojuego no disponible'}</b><time dateTime={entry.comparedAt} className="mt-1 block text-[11px] text-slate-400">{comparedDate(entry.comparedAt)}</time></span>
        {game && <Icon name="arrow" className="size-4 shrink-0 text-blue-400" />}
      </button>
    </li>;
  })}</ul>;
}

export default function ComparisonHistory() {
  const { user } = useStore();
  const { entries, available } = useComparisonHistory(user!._id);
  const [page, setPage] = useState(0);
  useEffect(() => { setPage(current => Math.min(current, Math.max(0, Math.ceil(entries.length / 12) - 1))); }, [entries.length]);
  const visible = entries.slice(page * 12, page * 12 + 12);
  const data = useProfileGames(visible.map(entry => entry.gameId));
  return <section className={panel}>
    <h1 className="text-xl font-extrabold">Juegos comparados{available ? ` (${entries.length})` : ''}</h1>
    <p className="mb-5 mt-2 text-xs leading-5 text-slate-400">{historyNote} Se conservan hasta 500 juegos distintos; volver a comparar uno actualiza su fecha.</p>
    {!available ? <ErrorState message="El navegador no permite acceder al historial local." />
      : !entries.length ? <Empty title="Aún no has comparado juegos aquí" text="Usa el botón Comparar precios de un videojuego para que aparezca en tu actividad." />
      : data.loading ? <p aria-live="polite" className="py-6 text-sm text-slate-400">Cargando juegos comparados…</p>
      : data.error ? <ErrorState message={data.error} retry={data.retry} />
      : <ComparisonList entries={visible} games={data.games} />}
    {entries.length > 12 && <nav aria-label="Paginación de juegos comparados" className="mt-5 flex items-center justify-center gap-4 text-sm"><button disabled={!page} onClick={() => setPage(n => n - 1)} className="rounded-lg border border-blue-500/30 px-4 py-2 disabled:opacity-40">Anterior</button><span>{page + 1} / {Math.ceil(entries.length / 12)}</span><button disabled={(page + 1) * 12 >= entries.length} onClick={() => setPage(n => n + 1)} className="rounded-lg border border-blue-500/30 px-4 py-2 disabled:opacity-40">Siguiente</button></nav>}
  </section>;
}
