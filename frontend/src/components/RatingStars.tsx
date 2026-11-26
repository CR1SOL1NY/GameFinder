import { useId, useState } from 'react';
import { Icon } from './common';

export const ratingLabel = (value: number) => `${value.toLocaleString('es-CL', { maximumFractionDigits: 1 })} de 5 estrellas`;

function Star({ fill }: { fill: number }) {
  return <span aria-hidden="true" className="relative inline-flex size-[1em] shrink-0 text-yellow-400">
    <Icon name="star" className="size-full" />
    <span className="absolute inset-0" style={{ clipPath: `inset(0 ${100 - Math.min(1, Math.max(0, fill)) * 100}% 0 0)` }}><Icon name="star" filled className="size-full" /></span>
  </span>;
}

export function RatingStars({ value, className = 'text-lg' }: { value: number; className?: string }) {
  return <span role="img" aria-label={ratingLabel(value)} className={`inline-flex gap-0.5 ${className}`}>{[0, 1, 2, 3, 4].map(index => <Star key={index} fill={value - index} />)}</span>;
}

export function StarRatingInput({ value, onChange, disabled = false }: { value: number; onChange: (value: number) => void; disabled?: boolean }) {
  const id = useId();
  const [hover, setHover] = useState<number | null>(null);
  return <fieldset disabled={disabled} aria-describedby={`${id}-help`} className="min-w-0">
    <legend className="mb-2 text-sm">Tu puntuación</legend>
    <div className="flex w-fit gap-0.5" onMouseLeave={() => setHover(null)}>
      {[0, 1, 2, 3, 4].map(index => <span key={index} className="relative grid size-12 place-items-center text-4xl">
        <Star fill={(hover ?? value) - index} />
        {[0.5, 1].map(part => {
          const score = index + part;
          return <label key={part} onMouseEnter={() => { if (!disabled) setHover(score); }} className={`absolute inset-y-0 z-10 w-1/2 cursor-pointer ${part === 0.5 ? 'left-0' : 'right-0'}`}>
            <input type="radio" name={`${id}-rating`} value={score} checked={value === score} onChange={() => { setHover(null); onChange(score); }} aria-label={ratingLabel(score)} required className="peer sr-only" />
            <span className="absolute inset-0 rounded-sm peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-blue-500" />
          </label>;
        })}
      </span>)}
    </div>
    <p className="mt-2 text-sm font-bold text-yellow-400" aria-live="polite">{value.toLocaleString('es-CL')} / 5</p>
    <p id={`${id}-help`} className="mt-1 text-xs text-slate-400">Puedes elegir medias estrellas tocando la mitad izquierda de cada estrella.</p>
  </fieldset>;
}
