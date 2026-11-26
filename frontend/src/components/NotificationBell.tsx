import { useEffect, useId, useRef, useState } from 'react';
import { useStore } from '../context/Store';
import { usePriceAlerts } from '../hooks/usePriceAlerts';
import { dateLabel, money } from '../games';
import { Icon, Img } from './common';

export default function NotificationBell() {
  const { user, wishlist, openGame, requireLogin } = useStore();
  const alerts = usePriceAlerts(user?._id || null, wishlist);
  const [open, setOpen] = useState(false);
  const id = useId();
  const root = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => { setOpen(false); }, [user?._id]);
  useEffect(() => {
    if (!open) return;
    panel.current?.focus();
    const outside = (event: PointerEvent) => { if (!root.current?.contains(event.target as Node)) setOpen(false); };
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') { setOpen(false); button.current?.focus(); } };
    document.addEventListener('pointerdown', outside); document.addEventListener('keydown', escape);
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', escape); };
  }, [open]);
  return <div ref={root} className="relative">
    <button ref={button} onClick={() => setOpen(value => !value)} aria-label={`Notificaciones${alerts.unread ? ` (${alerts.unread} sin leer)` : ''}`} aria-expanded={open} aria-controls={id} aria-haspopup="dialog" className="icon-button relative">
      <Icon name="bell" />
      {alerts.unread > 0 && <span className="absolute right-0 top-0 grid min-w-4 place-items-center rounded-full bg-blue-600 px-1 text-[9px] font-bold text-white">{alerts.unread > 9 ? '9+' : alerts.unread}</span>}
    </button>
    {open && <div ref={panel} tabIndex={-1} id={id} role="dialog" aria-label="Notificaciones de precios" className="fixed inset-x-3 top-20 z-[80] max-h-[calc(100dvh-10rem)] overflow-y-auto rounded-xl border border-blue-500/30 bg-panel p-4 shadow-2xl md:absolute md:inset-x-auto md:right-0 md:top-full md:mt-3 md:w-96">
      <div className="flex items-center justify-between gap-3"><h2 className="text-sm font-bold">Notificaciones</h2><button onClick={() => { setOpen(false); button.current?.focus(); }} aria-label="Cerrar notificaciones" className="grid size-9 place-items-center rounded-lg text-lg text-slate-300 hover:bg-blue-500/10">×</button></div>
      {!user ? <div className="py-5"><p className="text-sm text-slate-300">Inicia sesión para recibir avisos de tus juegos deseados.</p><button onClick={() => { setOpen(false); requireLogin('Inicia sesión para consultar las bajadas de precio de tu lista de deseados.'); }} className="mt-4 rounded-lg bg-blue-600 px-4 py-3 text-xs font-bold text-white">Iniciar sesión</button></div> : <>
        <p className="mt-2 text-xs leading-5 text-slate-400">Te avisamos cuando baja una oferta de tus deseados en la misma tienda, plataforma y moneda.</p>
        <div className="my-3 flex flex-wrap items-center justify-between gap-2"><button disabled={alerts.checking} onClick={alerts.refresh} className="min-h-10 text-xs font-bold text-blue-400 disabled:opacity-50">{alerts.checking ? 'Revisando precios…' : 'Actualizar precios'}</button>{alerts.unread > 0 && <button onClick={() => alerts.markRead()} className="min-h-10 text-xs text-blue-400">Marcar todas como leídas</button>}</div>
        {alerts.error && <p role="alert" className="mb-3 rounded-lg border border-rose-400/30 p-3 text-xs leading-5 text-rose-300">{alerts.error}</p>}
        {alerts.notifications.length ? <ul className="space-y-2">{alerts.notifications.map(item => <li key={item.id}>
          <button onClick={() => { alerts.markRead(item.id); setOpen(false); openGame(item.gameId); }} className={`flex w-full gap-3 rounded-lg border p-3 text-left transition hover:border-blue-400 ${item.read ? 'border-blue-500/20 bg-field' : 'border-blue-400/50 bg-blue-500/10'}`}>
            <Img src={item.imageUrl || '/cover-placeholder.svg'} fallback="/cover-placeholder.svg" alt="" className="h-12 w-16 shrink-0 rounded-md object-cover" />
            <span className="min-w-0"><span className="block text-xs font-bold">{!item.read && <span className="mr-1 text-blue-400" aria-label="Sin leer">●</span>}{item.title} bajó de precio</span><span className="mt-1 block text-xs text-slate-300">{item.store} · {item.platform || 'Plataforma no informada'}</span><span className="mt-1 block text-sm font-bold text-emerald-400"><span className="mr-2 text-xs font-normal text-slate-400 line-through">{money(item.previousPrice, item.currency)}</span>{money(item.price, item.currency)} <span className="text-[10px]">{item.currency}</span></span><time dateTime={item.createdAt} className="mt-1 block text-[10px] text-slate-400">{dateLabel(item.createdAt)}</time></span>
          </button>
        </li>)}</ul> : !alerts.error && <div className="rounded-lg border border-dashed border-blue-500/30 px-3 py-6 text-center"><Icon name="bell" className="mx-auto size-7 text-blue-400" /><p className="mt-3 text-sm font-bold">Sin bajadas de precio detectadas</p><p className="mt-2 text-xs leading-5 text-slate-400">{wishlist.length ? 'La primera revisión guarda los precios actuales. Las bajadas posteriores aparecerán aquí.' : 'Agrega juegos a tu lista de deseados para seguir sus precios.'}</p></div>}
        <p className="mt-4 text-[10px] leading-5 text-slate-400">Revisamos al abrir y cada minuto con la web visible. Los avisos se guardan en este navegador; no se envían con la web cerrada.</p>
      </>}
    </div>}
  </div>;
}
