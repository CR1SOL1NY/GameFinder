import { beforeEach, afterEach, it, expect, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import NotificationBell from '../src/components/NotificationBell';
import { StoreContext, type Store } from '../src/context/Store';
import { emptyPriceAlerts, reconcilePriceAlerts, type WatchedGame } from '../src/services/priceAlerts';

const game = (price: number): WatchedGame => ({ _id: 'juego', titulo: 'Juego de prueba', precios: [{ tiendaId: 'tienda', nombreTienda: 'Tienda de prueba', precio: price, moneda: 'CLP', plataforma: 'PC' }] });
const context: Store = { user: { _id: 'ana', nombre: 'Ana', correo: 'ana@example.com', fechaRegistro: '2026-01-01' }, wishlist: ['juego'], pendingWish: [], openGame: vi.fn(), compareGame: vi.fn(), toggleWish: vi.fn(), clearWish: vi.fn(), notify: vi.fn(), requireLogin: vi.fn(), refreshUser: vi.fn(), setUser: vi.fn(), logout: vi.fn() };
const element = (store = context) => <StoreContext.Provider value={store}><NotificationBell /></StoreContext.Provider>;
beforeEach(() => localStorage.clear());
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

it('muestra una bajada real en la campanita, permite leerla y abrir el juego', async () => {
  let price = 20000;
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ juegos: [game(price)] }))));
  const u = userEvent.setup();
  render(element());
  await waitFor(() => expect(JSON.parse(localStorage.getItem('gf-price-alerts-v1:ana') || '{}').checkedAt).toBeTruthy());
  await u.click(screen.getByRole('button', { name: 'Notificaciones', exact: true }));
  const popup = within(screen.getByRole('dialog', { name: 'Notificaciones de precios' }));
  expect(popup.getByText('Sin bajadas de precio detectadas')).toBeTruthy();
  price = 15000;
  await u.click(popup.getByRole('button', { name: 'Actualizar precios' }));
  await popup.findByText('Juego de prueba bajó de precio');
  expect(screen.getByRole('button', { name: 'Notificaciones (1 sin leer)', exact: true })).toBeTruthy();
  expect(popup.getByText('$20.000')).toBeTruthy();
  await u.click(popup.getByRole('button', { name: /Juego de prueba bajó de precio/ }));
  expect(context.openGame).toHaveBeenCalledWith('juego');
  expect(screen.queryByRole('dialog')).toBeNull();
  expect(screen.getByRole('button', { name: 'Notificaciones', exact: true })).toBeTruthy();
  expect(JSON.parse(localStorage.getItem('gf-price-alerts-v1:ana')!).notifications[0].read).toBe(true);
});

it('restaura avisos y cambia de cuenta sin mostrar notificaciones ajenas', async () => {
  const old = reconcilePriceAlerts(emptyPriceAlerts(), [game(20000)]);
  localStorage.setItem('gf-price-alerts-v1:ana', JSON.stringify(reconcilePriceAlerts(old, [game(15000)])));
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ juegos: [game(15000)] }))));
  const u = userEvent.setup();
  const view = render(element());
  await u.click(screen.getByRole('button', { name: 'Notificaciones (1 sin leer)', exact: true }));
  await u.click(screen.getByRole('button', { name: 'Marcar todas como leídas' }));
  expect(screen.getByRole('button', { name: 'Notificaciones', exact: true })).toBeTruthy();
  await u.keyboard('{Escape}');
  expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Notificaciones', exact: true }));
  view.rerender(element({ ...context, user: { ...context.user!, _id: 'otra' } }));
  await u.click(screen.getByRole('button', { name: 'Notificaciones', exact: true }));
  expect(screen.queryByText('Juego de prueba bajó de precio')).toBeNull();
  await screen.findByText('Sin bajadas de precio detectadas');
});

it('un visitante puede abrir la campana e iniciar sesión sin consultar datos privados', async () => {
  const fetcher = vi.fn();
  vi.stubGlobal('fetch', fetcher);
  const store = { ...context, user: null, wishlist: [] };
  const u = userEvent.setup();
  render(element(store));
  await u.click(screen.getByRole('button', { name: 'Notificaciones', exact: true }));
  await u.click(screen.getByRole('button', { name: 'Iniciar sesión' }));
  expect(store.requireLogin).toHaveBeenCalled();
  expect(fetcher).not.toHaveBeenCalled();
});

it('informa fallos de API y almacenamiento sin simular notificaciones guardadas', async () => {
  const fetcher = vi.fn(async () => new Response(JSON.stringify({ detail: 'Precios no disponibles' }), { status: 503 }));
  vi.stubGlobal('fetch', fetcher);
  const u = userEvent.setup();
  render(element());
  await u.click(screen.getByRole('button', { name: 'Notificaciones', exact: true }));
  expect((await screen.findByRole('alert')).textContent).toContain('Precios no disponibles');
  fetcher.mockImplementation(async () => new Response(JSON.stringify({ juegos: [game(15000)] })));
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new DOMException('Lleno', 'QuotaExceededError'); });
  await u.click(screen.getByRole('button', { name: 'Actualizar precios' }));
  await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('No pudimos guardar'));
  expect(screen.queryByText('Juego de prueba bajó de precio')).toBeNull();
});

it('revisa cada minuto visible y al volver a la pestaña, y cancela al cerrar sesión', async () => {
  const schedule = vi.spyOn(window, 'setInterval').mockReturnValue(41);
  const cancel = vi.spyOn(window, 'clearInterval').mockImplementation(() => {});
  const fetcher = vi.fn(async () => new Response(JSON.stringify({ juegos: [game(20000)] })));
  vi.stubGlobal('fetch', fetcher);
  const visibility = vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible');
  const view = render(element());
  fireEvent.click(screen.getByRole('button', { name: 'Notificaciones', exact: true }));
  await waitFor(() => expect(JSON.parse(localStorage.getItem('gf-price-alerts-v1:ana') || '{}').checkedAt, screen.queryByRole('alert')?.textContent || `Solicitudes: ${fetcher.mock.calls.length}`).toBeTruthy());
  expect(schedule).toHaveBeenCalledWith(expect.any(Function), 60000);
  const poll = schedule.mock.calls[0][0] as () => void;
  await act(async () => { poll(); });
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  await screen.findByRole('button', { name: 'Actualizar precios' });
  visibility.mockReturnValue('hidden');
  await act(async () => { poll(); });
  expect(fetcher).toHaveBeenCalledTimes(2);
  visibility.mockReturnValue('visible');
  await act(async () => { document.dispatchEvent(new Event('visibilitychange')); });
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(3));
  await screen.findByRole('button', { name: 'Actualizar precios' });
  view.rerender(element({ ...context, user: null, wishlist: [] }));
  expect(cancel).toHaveBeenCalledWith(41);
  await act(async () => { poll(); window.dispatchEvent(new Event('focus')); });
  expect(fetcher).toHaveBeenCalledTimes(3);
});
