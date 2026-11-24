import type { SystemRequirements } from './services/gameDetails';
/** Modelos de presentación: precio null significa desconocido; cero sí es válido. */
export type Platform = string;
export type StoreOffer = { id?: string; storeId: string; name: string; price: number; currency: string; platform?: string; url?: string; updatedAt?: string };
export type Game = { id: string; title: string; active?: boolean; imageUrl?: string; backgroundUrl?: string; summary?: string; features?: string[]; systemRequirements?: SystemRequirements; genres: string[]; platforms: string[]; price: number | null; rating: number; reviews: number; developer?: string; releaseDate?: string; year?: number; description: string; offers: StoreOffer[]; bestStore?: string };
export const coverOf = (g: Game) => g.imageUrl || '/cover-placeholder.svg';
export const posterOf = coverOf;
export const heroOf = coverOf;
export function money(value: number | null | undefined, currency = 'CLP') {
  if (value == null || !Number.isFinite(value)) return 'Precio no disponible';
  try { return new Intl.NumberFormat('es-CL', { style: 'currency', currency, maximumFractionDigits: currency === 'CLP' ? 0 : 2 }).format(value); }
  catch { return `${value.toLocaleString('es-CL')} ${currency}`; }
}
export const storesOf = (g: Game) => new Set(g.offers.map(o => o.storeId).filter(Boolean)).size;
export function safeUrl(value: unknown): string | undefined {
  if (typeof value !== 'string') return;
  try { const u = new URL(value); return ['https:', 'http:'].includes(u.protocol) && !u.username && !u.password ? u.href : undefined; } catch { return; }
}
export const dateLabel = (value?: string, calendar = false) => value && Number.isFinite(Date.parse(value)) ? new Intl.DateTimeFormat('es-CL', { dateStyle: 'medium', timeZone: calendar ? 'UTC' : 'America/Santiago' }).format(new Date(value)) : 'No informada';
