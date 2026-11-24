import { beforeEach, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GameDetail from '../src/views/GameDetail';
import { StoreContext, type Store } from '../src/context/Store';
import { mapearJuego, obtenerJuego, obtenerCatalogo } from '../src/api';
import { ApiError } from '../src/services/http';

vi.mock('../src/api', async importOriginal => ({ ...await importOriginal<typeof import('../src/api')>(), obtenerJuego: vi.fn(), obtenerCatalogo: vi.fn() }));
vi.mock('../src/services/reviews', async importOriginal => ({ ...await importOriginal<typeof import('../src/services/reviews')>(), getReviews: vi.fn(async () => []) }));

const game = mapearJuego({ _id: 'juego', titulo: 'Juego sintético de ficha', descripcion: 'Descripción completa procedente de la API de prueba.', descripcionCorta: 'Resumen breve de la API de prueba.', desarrollador: 'Desarrollador de prueba', fechaLanzamiento: '2025-02-01', imagenPortada: 'https://example.com/portada.jpg', imagenFondo: 'https://example.com/fondo.jpg', generos: ['RPG'], plataformas: ['PC', 'PS5'], promedioCalificaciones: 4.5, totalCalificaciones: 12, caracteristicas: ['Exploración de prueba', 'Combates de prueba'], requisitosSistema: { plataforma: 'PC', minimos: { sistemaOperativo: 'SO mínimo de prueba', procesador: 'CPU mínima de prueba', memoria: '8 GB de prueba' }, recomendados: { procesador: 'CPU recomendada de prueba', almacenamiento: 'Espacio recomendado de prueba' } }, precios: [{ tiendaId: 'tienda', precio: 15000, moneda: 'CLP', plataforma: 'PC', urlProducto: 'https://example.com/comprar' }] }, [{ _id: 'tienda', nombre: 'Tienda de prueba' }]);
const context: Store = { user: null, wishlist: [], pendingWish: [], openGame: vi.fn(), compareGame: vi.fn(), toggleWish: vi.fn(), clearWish: vi.fn(), notify: vi.fn(), requireLogin: vi.fn(), refreshUser: vi.fn(), setUser: vi.fn(), logout: vi.fn() };
const element = (id = 'juego', back = vi.fn()) => <StoreContext.Provider value={context}><GameDetail id={id} back={back} /></StoreContext.Provider>;
beforeEach(() => {
  vi.mocked(obtenerJuego).mockReset().mockResolvedValue(game);
  vi.mocked(obtenerCatalogo).mockReset().mockResolvedValue({ items: [], total: 0, skip: 0, limit: 24 });
});

it('muestra portada, fondo, resumen, características y requisitos reales sin descuentos ni stock inventados', async () => {
  render(element());
  await screen.findByRole('heading', { name: game.title });
  expect(screen.getByRole('img', { name: `Portada de ${game.title}` }).getAttribute('src')).toBe(game.imageUrl);
  expect(document.querySelector('.detail-hero-image')?.getAttribute('src')).toBe(game.backgroundUrl);
  expect(screen.getByText('Resumen breve de la API de prueba.')).toBeTruthy();
  expect(screen.getByText('Descripción completa procedente de la API de prueba.')).toBeTruthy();
  expect(screen.getByText('Desarrollador de prueba')).toBeTruthy();
  expect(screen.getByText('2025')).toBeTruthy();
  expect(screen.getByText('CPU mínima de prueba')).toBeTruthy();
  expect(screen.getByText('CPU recomendada de prueba')).toBeTruthy();
  expect(screen.getByText('Exploración de prueba')).toBeTruthy();
  const tabs = within(screen.getByRole('tablist', { name: 'Información del videojuego' }));
  expect(tabs.getAllByRole('tab').map(item => item.textContent)).toEqual(['Información', 'Reseñas']);
  expect(screen.getByRole('complementary', { name: 'Tiendas y precios del videojuego' })).toBeTruthy();
  expect(screen.getByRole('link', { name: /Ver oferta/ }).getAttribute('href')).toBe('https://example.com/comprar');
  expect(screen.queryByText(/En stock/)).toBeNull();
  expect(screen.queryByText(/33%/)).toBeNull();
});

it('conserva la comparación lateral y permite navegar las pestañas con teclado', async () => {
  const u = userEvent.setup();
  render(element());
  const info = await screen.findByRole('tab', { name: 'Información' });
  info.focus();
  await u.keyboard('[ArrowRight]');
  const reviews = screen.getByRole('tab', { name: 'Reseñas' });
  expect(reviews.getAttribute('aria-selected')).toBe('true');
  expect(document.activeElement).toBe(reviews);
  await screen.findByRole('heading', { name: 'Calificaciones de la comunidad' });
  expect(screen.getByRole('table')).toBeTruthy();
  await u.keyboard('[Home]');
  expect(info.getAttribute('aria-selected')).toBe('true');
  expect(screen.getByRole('heading', { name: 'Descripción del juego' })).toBeTruthy();
});

it('el botón de valoración abre reseñas y el de deseados conserva su acción real', async () => {
  const u = userEvent.setup();
  render(element());
  const hero = within(await screen.findByRole('region', { name: 'Presentación del videojuego' }));
  await u.click(hero.getByRole('button', { name: /4,5.*12 reseñas/ }));
  expect(screen.getByRole('tab', { name: 'Reseñas' }).getAttribute('aria-selected')).toBe('true');
  await u.click(hero.getByRole('button', { name: 'Añadir a la lista de deseados' }));
  expect(context.toggleWish).toHaveBeenCalledWith(game);
});

it('no inventa características, requisitos, portadas o precios cuando faltan', async () => {
  vi.mocked(obtenerJuego).mockResolvedValue({ ...game, imageUrl: undefined, backgroundUrl: undefined, features: [], systemRequirements: undefined, offers: [], price: null });
  render(element());
  await screen.findByRole('heading', { name: game.title });
  expect(screen.queryByRole('heading', { name: 'Lo que encontrarás en el juego' })).toBeNull();
  expect(screen.getAllByText('La fuente de datos todavía no informa estos requisitos.')).toHaveLength(2);
  expect(screen.queryByText('CPU mínima de prueba')).toBeNull();
  expect(screen.getByText('Precio no disponible')).toBeTruthy();
  expect(screen.getByRole('img', { name: `Portada de ${game.title}` }).getAttribute('src')).toBe('/cover-placeholder.svg');
  expect(screen.queryByRole('link', { name: /Ver oferta/ })).toBeNull();
});

it('informa errores y permite volver a consultar la ficha sin mostrar un éxito falso', async () => {
  vi.mocked(obtenerJuego).mockRejectedValueOnce(new ApiError(503, 'Catálogo no disponible'));
  const back = vi.fn();
  const u = userEvent.setup();
  render(element('juego', back));
  expect((await screen.findByRole('alert')).textContent).toContain('Catálogo no disponible');
  expect(screen.queryByRole('heading', { name: game.title })).toBeNull();
  await u.click(screen.getByRole('button', { name: 'Volver al catálogo' }));
  expect(back).toHaveBeenCalledOnce();
  await u.click(screen.getByRole('button', { name: 'Volver a intentar' }));
  await screen.findByRole('heading', { name: game.title });
});
