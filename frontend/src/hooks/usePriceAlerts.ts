import { useEffect, useMemo, useState, useSyncExternalStore } from 'react';
import { request, errorMessage } from '../services/http';
import { emptyPriceAlerts, parsePriceAlerts, reconcilePriceAlerts, type PriceAlertsState, type WatchedGame } from '../services/priceAlerts';

const eventName = 'gamefinder-price-alerts';
const unavailable = '!storage-unavailable';
const keyFor = (userId: string) => `gf-price-alerts-v1:${userId}`;

function persist(key: string, value: PriceAlertsState) {
  try { localStorage.setItem(key, JSON.stringify(value)); }
  catch { throw new Error('No pudimos guardar las notificaciones en este navegador.'); }
  window.dispatchEvent(new CustomEvent(eventName, { detail: key }));
}

export function usePriceAlerts(userId: string | null, wishlist: string[]) {
  const key = userId ? keyFor(userId) : null;
  const wishKey = JSON.stringify([...new Set(wishlist)].sort());
  const [refresh, setRefresh] = useState(0);
  const [status, setStatus] = useState({ key, checking: false, error: '' });
  function snapshot() { try { return key ? localStorage.getItem(key) : null; } catch { return unavailable; } }
  function subscribe(callback: () => void) {
    const storage = (event: StorageEvent) => { if (key && (event.key === key || event.key === null)) callback(); };
    const local = (event: Event) => { if (key && (event as CustomEvent).detail === key) callback(); };
    window.addEventListener('storage', storage); window.addEventListener(eventName, local);
    return () => { window.removeEventListener('storage', storage); window.removeEventListener(eventName, local); };
  }
  const raw = useSyncExternalStore(subscribe, snapshot, () => null);
  const data = useMemo(() => key ? parsePriceAlerts(raw) : emptyPriceAlerts(), [key, raw]);
  useEffect(() => {
    if (!key) return;
    const controller = new AbortController();
    let live = true, inFlight = false;
    async function check(initial = false) {
      if (!live || !key || inFlight || (!initial && document.visibilityState === 'hidden')) return;
      inFlight = true;
      setStatus({ key, checking: true, error: '' });
      try {
        const result = await request<{ juegos: WatchedGame[] }>('/usuarios/me/precios-deseados', { signal: controller.signal });
        if (!Array.isArray(result.juegos)) throw new Error('No pudimos interpretar los precios de tus deseados.');
        if (live) persist(key, reconcilePriceAlerts(parsePriceAlerts(localStorage.getItem(key)), result.juegos));
        if (live) setStatus({ key, checking: false, error: '' });
      } catch (err) {
        if (live) setStatus({ key, checking: false, error: errorMessage(err) });
      } finally { inFlight = false; }
    }
    void check(true);
    const onVisible = () => { void check(); };
    const timer = window.setInterval(onVisible, 60_000);
    window.addEventListener('focus', onVisible); window.addEventListener('online', onVisible); document.addEventListener('visibilitychange', onVisible);
    return () => { live = false; controller.abort(); window.clearInterval(timer); window.removeEventListener('focus', onVisible); window.removeEventListener('online', onVisible); document.removeEventListener('visibilitychange', onVisible); };
  }, [key, wishKey, refresh]);
  function markRead(id?: string) {
    if (!key) return;
    try {
      const current = parsePriceAlerts(localStorage.getItem(key));
      persist(key, { ...current, notifications: current.notifications.map(item => !id || item.id === id ? { ...item, read: true } : item) });
    } catch { setStatus({ key, checking: false, error: 'No pudimos guardar el estado de las notificaciones en este navegador.' }); }
  }
  return { ...data, unread: data.notifications.filter(item => !item.read).length, checking: status.key === key && status.checking, error: raw === unavailable ? 'El navegador no permite guardar las notificaciones.' : status.key === key ? status.error : '', refresh: () => setRefresh(n => n + 1), markRead };
}
