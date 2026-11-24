import { type StoreOffer } from '../games';
import { request, jsonBody } from './http';
import type { TiendaAPI } from '../api';

/** Ausencia de configuración no equivale a soporte confirmado para todas las plataformas. */
export function storePlatforms(store?: TiendaAPI): string[] | undefined {
  const platforms = store?.plataformas;
  if (!Array.isArray(platforms)) return;
  const values = [...new Set(platforms.filter(p => typeof p === 'string' && p.trim()).map(p => p.trim()))];
  return values.length ? values : undefined;
}
export function compatiblePlatforms(platforms: string[], store?: TiendaAPI): string[] {
  if (!store) return [];
  const supported = storePlatforms(store);
  return supported ? platforms.filter(p => supported.includes(p)) : platforms;
}

export type OfferDraft = {
  tiendaId: string;
  precio: number;
  moneda: string;
  plataforma: string;
  urlProducto: string | null;
};

/** Los registros antiguos se seleccionan por su clave completa, nunca solo por tienda. */
export function offerPath(gameId: string, offer: StoreOffer) {
  const base = `/juegos/${encodeURIComponent(gameId)}`;
  if (offer.id) return `${base}/ofertas/${encodeURIComponent(offer.id)}`;
  const query = new URLSearchParams({ moneda: offer.currency });
  if (offer.platform) query.set('plataforma', offer.platform);
  else query.set('sin_plataforma', 'true');
  return `${base}/tiendas/${encodeURIComponent(offer.storeId)}?${query}`;
}

export async function saveOffer(gameId: string, draft: OfferDraft, existing?: StoreOffer) {
  if (!existing) return request(`/juegos/${encodeURIComponent(gameId)}/ofertas`, jsonBody('POST', draft));
  const previous = { precio: existing.price, moneda: existing.currency, plataforma: existing.platform || null, urlProducto: existing.url || null };
  const changes = Object.fromEntries((Object.keys(previous) as (keyof typeof previous)[])
    .filter(key => draft[key] !== previous[key]).map(key => [key, draft[key]]));
  if (!Object.keys(changes).length) throw new Error('No hay cambios para guardar.');
  return request(offerPath(gameId, existing), jsonBody('PUT', changes));
}
