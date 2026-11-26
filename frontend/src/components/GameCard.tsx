import { Icon, Img } from './common';
import { useStore } from '../context/Store';
import { coverOf, money, storesOf, type Game } from '../games';
export function WishButton({ game, className = '', variant = 'icon' }: { game: Game; className?: string; variant?: 'icon' | 'label' }) {
  const { wishlist, toggleWish, pendingWish } = useStore();
  const on = wishlist.includes(game.id);
  return (
    <button disabled={pendingWish.includes(game.id)} onClick={(e) => { e.stopPropagation(); void toggleWish(game); }} aria-pressed={on} aria-label={on ? 'Quitar de la lista de deseados' : 'Añadir a la lista de deseados'} className={`${variant === 'label' ? 'inline-flex min-h-11 items-center justify-center gap-2 rounded-full border border-blue-400/50 bg-[#111827]/85 px-5 py-2 text-xs font-bold transition hover:bg-blue-600/25' : 'grid size-8 place-items-center rounded-full bg-black/45 backdrop-blur transition hover:scale-110'} ${on ? 'text-rose-400' : 'text-white'} ${className}`}>
      <Icon name="heart" className="size-4" filled={on} />
      {variant === 'label' && <span>{pendingWish.includes(game.id) ? 'Guardando…' : on ? 'En tu lista de deseados' : 'Añadir a lista de deseados'}</span>}
    </button>
  );
}

export function GameCard({ game, horizontal = false }: { game: Game; horizontal?: boolean }) {
  const { openGame, compareGame } = useStore();
  return (
    <article className={`group overflow-hidden rounded-xl border border-blue-500/30 bg-card transition hover:-translate-y-0.5 hover:border-blue-400/70 ${horizontal ? 'flex' : ''}`}>
      <div className={`relative cursor-pointer overflow-hidden ${horizontal ? 'grid w-[42%] shrink-0 place-items-center bg-black' : 'aspect-[460/215] bg-black'}`}>
        <button onClick={() => openGame(game.id)} aria-label={`Ver ${game.title}`} className="block size-full"><Img src={coverOf(game)} fallback="/cover-placeholder.svg" alt={game.title} className={`${horizontal ? 'max-h-full w-full object-contain' : 'size-full object-cover'} object-center transition duration-500 group-hover:scale-105`} /></button>
        <WishButton game={game} className="absolute right-2 top-2" />
      </div>
      <div className="flex min-w-0 flex-1 flex-col p-3">
        <h3 className="text-sm font-bold"><button onClick={() => openGame(game.id)} className="text-left hover:text-blue-400">{game.title}</button></h3>
        <div className="mt-2 flex flex-wrap gap-1">{game.platforms.map((p) => <span key={p} className="rounded bg-blue-600/25 px-2 py-0.5 text-[9px] font-bold text-blue-300">{p}</span>)}</div>
        <p className="mt-2 truncate text-[10px] text-slate-400">{game.genres.slice(0, 3).join(' · ')}</p>
        <div className="mt-auto pt-3">
          <p className="text-[9px] text-blue-400">Tiendas identificadas ({storesOf(game)})</p>
          <p className="text-[10px] text-slate-400">Desde · CLP</p>
          <p className="flex items-baseline gap-2 text-lg font-black">{money(game.price)}</p><p className="text-[10px] text-slate-400">{game.bestStore ?? "Sin oferta CLP registrada"}</p>
        </div>
        <button onClick={() => compareGame(game)} className="mt-2 flex w-full items-center justify-center gap-2 rounded-md bg-blue-600 py-2 text-[10px] font-bold text-white transition hover:bg-blue-500">Comparar precios <Icon name="arrow" className="size-3.5" /></button>
      </div>
    </article>
  );
}

