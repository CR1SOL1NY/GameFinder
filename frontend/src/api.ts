import { safeUrl, type Game, type StoreOffer } from './games';
import { request } from './services/http';
import { detailText, featuresFromAPI, requirementsFromAPI, type ExtraGameInfoAPI } from './services/gameDetails';
export interface PrecioAPI { ofertaId?: string; tiendaId?: string; precio?: number; moneda?: string; plataforma?: string | null; urlProducto?: string; fechaActualizacion?: string }
export interface JuegoAPI extends ExtraGameInfoAPI { _id: string; titulo: string; activo?: boolean; descripcion?: string; imagenPortada?: string; desarrollador?: string; fechaLanzamiento?: string; generos?: string[]; plataformas?: string[]; precios?: PrecioAPI[]; promedioCalificaciones?: number; totalCalificaciones?: number }
export interface TiendaAPI { _id: string; nombre: string; url_base?: string | null; plataformas?: string[] | null }
export interface Facets { generos: string[]; plataformas: string[] }
export interface CatalogParams { q?: string; genres?: string[]; platforms?: string[]; min?: string; max?: string; sort?: string; page?: number; priced?: boolean }
export interface CatalogPage { items: Game[]; total: number; skip: number; limit: number }
let stores: Promise<TiendaAPI[]> | undefined;
export function obtenerTiendas(refresh = false) { if (!stores || refresh) stores = request<TiendaAPI[]>('/tiendas/').catch(e => { stores = undefined; throw e; }); return stores; }
export function mapearJuego(item: JuegoAPI, tiendas: TiendaAPI[]): Game {
  if (!item || typeof item._id !== 'string' || typeof item.titulo !== 'string') throw new Error('El catálogo contiene un juego con formato inesperado.');
  const names = new Map(tiendas.map(t => [t._id, t.nombre]));
  const offers: StoreOffer[] = (Array.isArray(item.precios) ? item.precios : []).filter(p => typeof p.precio === 'number' && Number.isFinite(p.precio) && p.precio >= 0).map(p => ({ id: p.ofertaId, storeId: p.tiendaId || '', name: names.get(p.tiendaId || '') || 'Tienda no identificada', price: p.precio!, currency: p.moneda || 'Sin moneda', platform: p.plataforma || undefined, url: safeUrl(p.urlProducto), updatedAt: p.fechaActualizacion }));
  const clp = offers.filter(p => p.currency === 'CLP').sort((a,b) => a.price - b.price);
  const date = item.fechaLanzamiento && Number.isFinite(Date.parse(item.fechaLanzamiento)) ? item.fechaLanzamiento : undefined;
  return { id: item._id, title: item.titulo, active: item.activo !== false, description: item.descripcion || 'Sin descripción disponible.', imageUrl: safeUrl(item.imagenPortada), backgroundUrl: safeUrl(item.imagenFondo), summary: detailText(item.descripcionCorta), features: featuresFromAPI(item.caracteristicas), systemRequirements: requirementsFromAPI(item.requisitosSistema), genres: (item.generos || []).filter(g => typeof g === 'string'), platforms: (item.plataformas || []).filter(p => typeof p === 'string'), developer: item.desarrollador || undefined, releaseDate: date, year: date ? new Date(date).getUTCFullYear() : undefined, offers, price: clp[0]?.price ?? null, bestStore: clp[0]?.name, rating: item.promedioCalificaciones || 0, reviews: item.totalCalificaciones || 0 };
}
export async function obtenerCatalogo(params: CatalogParams = {}, signal?: AbortSignal): Promise<CatalogPage> {
  const query = new URLSearchParams({ limit: '24', skip: String(((params.page || 1) - 1) * 24), orden: params.sort || 'titulo' });
  if (params.q) query.set('q', params.q);
  params.genres?.forEach(g => query.append('genero', g));
  params.platforms?.forEach(p => query.append('plataforma', p));
  if (params.min !== undefined && params.min !== '') query.set('precio_min', params.min);
  else if (params.priced) query.set('precio_min', '0');
  if (params.max !== undefined && params.max !== '') query.set('precio_max', params.max);
  const [page, tiendas] = await Promise.all([request<{ items: JuegoAPI[]; total: number; skip: number; limit: number }>(`/juegos/catalogo?${query}`, {signal}), obtenerTiendas()]);
  if (!Array.isArray(page.items)) throw new Error('La API devolvió un catálogo con formato inesperado.');
  return { ...page, items: page.items.map(g => mapearJuego(g, tiendas)) };
}
export async function obtenerJuego(id: string, signal?: AbortSignal) { const [game, tiendas] = await Promise.all([request<JuegoAPI>(`/juegos/${encodeURIComponent(id)}`, {signal}), obtenerTiendas()]); return mapearJuego(game, tiendas); }
export const obtenerFiltros = (signal?: AbortSignal) => request<Facets>('/juegos/filtros', {signal});

export async function obtenerCatalogoAdmin(q: string) { const [page,tiendas]=await Promise.all([request<{items:JuegoAPI[];total:number}>(`/admin/juegos?q=${encodeURIComponent(q)}`),obtenerTiendas()]);return {...page,items:page.items.map(g=>mapearJuego(g,tiendas))}; }
export async function obtenerJuegoAdmin(id: string, signal?: AbortSignal) { const [game,tiendas]=await Promise.all([request<JuegoAPI>(`/admin/juegos/${encodeURIComponent(id)}`,{signal}),obtenerTiendas()]);return mapearJuego(game,tiendas); }
