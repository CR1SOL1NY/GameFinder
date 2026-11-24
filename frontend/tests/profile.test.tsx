import { beforeEach, afterEach, describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StoreContext, type Store } from '../src/context/Store';
import ProfileOverview from '../src/components/profile/ProfileOverview';
import ComparisonHistory from '../src/components/profile/ComparisonHistory';
import { recordComparison } from '../src/services/comparisons';
import type { ReviewSummary } from '../src/services/reviews';

beforeEach(() => localStorage.clear());
afterEach(() => vi.unstubAllGlobals());
const user = { _id: 'ana', nombre: 'Ana Prueba', correo: 'ana@example.com', fechaRegistro: '2025-01-01', preferencias: { precioMin: 5000, precioMax: 50000, generos: ['RPG', 'Acción'], plataformas: ['PC'] }, listaDeseados: [1, 2, 3, 4].map(i => ({ juegoId: `d${i}`, fechaAgregado: `2026-01-0${i}` })) };
const context: Store = { user, wishlist: ['d1', 'd2', 'd3', 'd4'], pendingWish: [], openGame: vi.fn(), compareGame: vi.fn(), toggleWish: vi.fn(), clearWish: vi.fn(), notify: vi.fn(), requireLogin: vi.fn(), refreshUser: vi.fn(), setUser: vi.fn(), logout: vi.fn() };
const summary: ReviewSummary = { total: 4, promedio: 4.25, ultimas: [4, 3, 2].map(i => ({ _id: `r${i}`, juegoId: `j${i}`, usuarioId: 'ana', puntaje: 4, comentario: `Comentario de prueba ${i}`, fecha: `2026-01-0${i}`, juego: { _id: `j${i}`, titulo: `Juego reseñado ${i}` } })) };

function api(data: ReviewSummary | null) {
  vi.stubGlobal('fetch', vi.fn(async (input: string) => {
    const path = new URL(input).pathname;
    if (path.endsWith('/resumen-calificaciones')) return new Response(JSON.stringify(data || { detail: 'No pudimos cargar tus reseñas' }), { status: data ? 200 : 503 });
    if (path === '/tiendas/') return new Response('[]');
    if (path.endsWith('/recomendaciones')) return new Response(JSON.stringify({ recomendaciones: [] }));
    const id = path.split('/').at(-1);
    return new Response(JSON.stringify({ _id: id, titulo: `Juego de prueba ${id}`, plataformas: ['PC'], generos: [], precios: [] }));
  }));
}

function overview(value = context) {
  const setSection = vi.fn();
  render(<StoreContext.Provider value={value}><ProfileOverview setSection={setSection} /></StoreContext.Provider>);
  return setSection;
}

describe('Resumen de perfil con datos reales de los servicios', () => {
  it('muestra tres reseñas, tres comparaciones, preferencias y contadores; Ver todos navega', async () => {
    api(summary);
    for (let i = 1; i <= 4; i++) recordComparison('ana', `c${i}`, `2026-01-0${i}`);
    const setSection = overview();
    const u = userEvent.setup();
    const reviews = within(await screen.findByRole('region', { name: 'Últimas reseñas' }));
    await reviews.findByText('Comentario de prueba 4');
    expect(reviews.getAllByRole('article')).toHaveLength(3);
    expect(reviews.queryByText('Comentario de prueba 1')).toBeNull();
    const activity = within(screen.getByRole('region', { name: 'Tu actividad reciente' }));
    await activity.findByText('Juego de prueba c4');
    expect(activity.getAllByRole('listitem')).toHaveLength(3);
    expect(activity.queryByText('Juego de prueba c1')).toBeNull();
    const stats = within(screen.getByRole('group', { name: 'Estadísticas de tu perfil' }));
    expect(stats.getByRole('button', { name: /Juegos en tu lista de deseados/ }).textContent).toContain('4');
    expect(stats.getByRole('button', { name: /Juegos comparados/ }).textContent).toContain('4');
    expect(stats.getByRole('button', { name: /Promedio de mis reseñas/ }).textContent).toContain('4,3');
    const preferences = within(screen.getByRole('region', { name: 'Mis preferencias' }));
    expect(preferences.getByText('5.000', { exact: false })).toBeTruthy();
    expect(preferences.getByText('50.000', { exact: false })).toBeTruthy();
    expect(preferences.getAllByRole('listitem').map(item => item.textContent)).toEqual(['RPG', 'Acción']);
    expect(preferences.queryByText('Géneros preferidos')).toBeNull();
    expect(screen.queryByText('Resumen de compras')).toBeNull();
    await u.click(reviews.getByRole('button', { name: /Ver todas las reseñas/ }));
    expect(setSection).toHaveBeenLastCalledWith('Mis calificaciones');
    await u.click(activity.getByRole('button', { name: /Ver todos los juegos comparados/ }));
    expect(setSection).toHaveBeenLastCalledWith('Juegos comparados');
    await u.click(preferences.getByRole('button', { name: 'Editar mis preferencias' }));
    expect(setSection).toHaveBeenLastCalledWith('Configuración');
  });
  it('muestra estados vacíos sin compras, promedio ficticio ni actividad de otra cuenta', async () => {
    api({ total: 0, promedio: null, ultimas: [] });
    recordComparison('otra', 'juego-de-otra-persona');
    overview({ ...context, user: { ...user, preferencias: null, listaDeseados: [] }, wishlist: [] });
    await screen.findByText('Todavía no has publicado reseñas. Califica un juego desde su ficha.');
    expect(screen.getByText('Tu próxima comparación aparecerá aquí')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Tu lista de deseados (0)' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: /Ver todas las reseñas/ })).toBeNull();
    expect(screen.queryByRole('button', { name: /Ver todos los juegos comparados/ })).toBeNull();
    expect(screen.getByRole('button', { name: /Promedio de mis reseñas/ }).textContent).toContain('—');
    expect(screen.queryByText('juego-de-otra-persona')).toBeNull();
  });
  it('muestra el fallo de API y no lo transforma en cero reseñas', async () => {
    api(null);
    overview({ ...context, user: { ...user, listaDeseados: [] }, wishlist: [] });
    expect((await screen.findByRole('alert')).textContent).toContain('No pudimos cargar tus reseñas');
    const stats = within(screen.getByRole('group', { name: 'Estadísticas de tu perfil' }));
    expect(stats.getByRole('button', { name: /Promedio de mis reseñas/ }).textContent).toContain('No disponible');
    expect(screen.queryByText('Todavía no has publicado reseñas. Califica un juego desde su ficha.')).toBeNull();
  });
});


it('la lista completa pagina más de doce juegos sin perder el resto del historial', async () => {
  api(summary);
  for (let i = 1; i <= 13; i++) recordComparison('ana', `historial-${i}`, new Date(2026, 0, i).toISOString());
  const u = userEvent.setup();
  render(<StoreContext.Provider value={context}><ComparisonHistory /></StoreContext.Provider>);
  await screen.findByText('Juego de prueba historial-13');
  expect(screen.getAllByRole('listitem')).toHaveLength(12);
  const pagination = within(screen.getByRole('navigation', { name: 'Paginación de juegos comparados' }));
  expect((pagination.getByRole('button', { name: 'Anterior' }) as HTMLButtonElement).disabled).toBe(true);
  await u.click(pagination.getByRole('button', { name: 'Siguiente' }));
  await screen.findByText('Juego de prueba historial-1');
  expect(screen.getAllByRole('listitem')).toHaveLength(1);
  expect(pagination.getByText('2 / 2')).toBeTruthy();
  expect((pagination.getByRole('button', { name: 'Siguiente' }) as HTMLButtonElement).disabled).toBe(true);
});
