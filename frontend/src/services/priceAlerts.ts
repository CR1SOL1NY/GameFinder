/** Avisos locales a partir de instantáneas reales. No convierte monedas ni asigna plataformas. */
import { safeUrl } from '../games';
import type { PrecioAPI } from '../api';

export interface WatchedGame { _id: string; titulo: string; imagenPortada?: string; precios?: (PrecioAPI & { nombreTienda?: string | null })[] }
export interface PriceAlert { id: string; gameId: string; title: string; store: string; platform?: string; currency: string; previousPrice: number; price: number; createdAt: string; read: boolean; imageUrl?: string; url?: string }
export interface PriceAlertsState { prices: Record<string, number>; notifications: PriceAlert[]; checkedAt?: string }
export const emptyPriceAlerts = (): PriceAlertsState => ({ prices: {}, notifications: [] });
const validPrice = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value) && value >= 0;

export function parsePriceAlerts(raw: string | null): PriceAlertsState {
  try {
    const data = JSON.parse(raw || '{}');
    const prices = data?.prices && typeof data.prices === 'object' && !Array.isArray(data.prices)
      ? Object.fromEntries(Object.entries(data.prices).filter(([key, value]) => key.length <= 1000 && validPrice(value))) as Record<string, number> : {};
    const notifications: PriceAlert[] = Array.isArray(data?.notifications) ? data.notifications.slice(0, 100).filter((item: PriceAlert) => item && typeof item.id === 'string' && typeof item.gameId === 'string' && typeof item.title === 'string' && typeof item.store === 'string' && typeof item.currency === 'string' && /^[A-Z]{3}$/.test(item.currency) && validPrice(item.price) && validPrice(item.previousPrice) && item.price < item.previousPrice && typeof item.createdAt === 'string' && Number.isFinite(Date.parse(item.createdAt))).map((item: PriceAlert) => ({ ...item, read: item.read === true, imageUrl: safeUrl(item.imageUrl), url: safeUrl(item.url), platform: typeof item.platform === 'string' ? item.platform : undefined })) : [];
    return { prices, notifications, checkedAt: typeof data?.checkedAt === 'string' && Number.isFinite(Date.parse(data.checkedAt)) ? data.checkedAt : undefined };
  } catch { return emptyPriceAlerts(); }
}

export function reconcilePriceAlerts(previous: PriceAlertsState, games: WatchedGame[], now = new Date().toISOString()): PriceAlertsState {
  const current = new Map<string, { game: WatchedGame; offer: NonNullable<WatchedGame['precios']>[number] }>();
  const duplicates = new Set<string>();
  const active = new Set(games.map(game => game._id));
  for (const game of games) {
    for (const offer of game.precios || []) {
      if (!offer.tiendaId || !validPrice(offer.precio) || !offer.moneda || !/^[A-Z]{3}$/.test(offer.moneda)) continue;
      const key = JSON.stringify([game._id, offer.tiendaId, offer.plataforma || null, offer.moneda]);
      if (current.has(key)) duplicates.add(key);
      current.set(key, { game, offer });
    }
  }
  const prices: Record<string, number> = {};
  const added: PriceAlert[] = [];
  for (const [key, { game, offer }] of current) {
    // Datos heredados ambiguos no permiten identificar una bajada fiable.
    if (duplicates.has(key)) continue;
    const price = offer.precio!;
    prices[key] = price;
    const old = previous.prices[key];
    if (validPrice(old) && price < old) added.push({
      id: JSON.stringify([key, now, old, price]), gameId: game._id, title: game.titulo,
      store: offer.nombreTienda || 'Tienda no identificada', platform: offer.plataforma || undefined,
      currency: offer.moneda!, previousPrice: old, price, createdAt: now, read: false,
      imageUrl: safeUrl(game.imagenPortada), url: safeUrl(offer.urlProducto),
    });
  }
  return { prices, notifications: [...added, ...previous.notifications.filter(item => active.has(item.gameId))].slice(0, 100), checkedAt: now };
}
