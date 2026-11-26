import { useStore } from '../../context/Store';
import { dateLabel, safeUrl } from '../../games';
import { type Review } from '../../services/reviews';
import { Icon, Img } from '../common';
import { RatingStars } from '../RatingStars';

export default function ReviewCard({ review, compact = false }: { review: Review; compact?: boolean }) {
  const { openGame } = useStore();
  const available = !!review.juego;
  const title = review.juego?.titulo || 'Videojuego no disponible';
  return (
    <article className="flex min-w-0 flex-col rounded-xl border border-blue-500/25 bg-field p-4">
      <div className="flex items-center gap-3">
        <Img src={safeUrl(review.juego?.imagenPortada) || '/cover-placeholder.svg'} fallback="/cover-placeholder.svg" alt="" className="h-12 w-16 shrink-0 rounded-md object-cover" />
        <h3 className="min-w-0 text-sm font-bold"><button disabled={!available} onClick={() => openGame(review.juegoId)} className="text-left hover:text-blue-400 disabled:text-slate-400">{title}</button></h3>
      </div>
      <div className="mt-3"><RatingStars value={review.puntaje}/></div>
      <p className={`mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-slate-300 ${compact ? 'line-clamp-3' : ''}`}>{review.comentario || 'Sin comentario'}</p>
      <p className="mt-auto pt-3 text-xs text-slate-400"><time dateTime={review.fecha}>{dateLabel(review.fecha)}</time></p>
      {!compact && available && <button onClick={() => openGame(review.juegoId)} className="mt-3 inline-flex items-center gap-2 self-start py-2 text-xs font-bold text-blue-400">Ver juego y editar mi calificación <Icon name="arrow" className="size-3.5" /></button>}
    </article>
  );
}
