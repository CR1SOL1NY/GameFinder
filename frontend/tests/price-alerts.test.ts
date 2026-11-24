import { it, expect } from 'vitest';
import { emptyPriceAlerts, parsePriceAlerts, reconcilePriceAlerts, type WatchedGame } from '../src/services/priceAlerts';
const game: WatchedGame = { _id: 'juego', titulo: 'Juego de prueba', precios: [{ tiendaId: 'tienda', precio: 20000, moneda: 'CLP', plataforma: 'PC' }] };
const snapshot = (price: number) => [{ ...game, precios: [{ ...game.precios![0], precio: price }] }];

it('la primera lectura guarda una referencia sin inventar una bajada', () => {
  const state = reconcilePriceAlerts(emptyPriceAlerts(), [game]);
  expect(Object.values(state.prices)).toEqual([20000]);
  expect(state.notifications).toEqual([]);
});
it('detecta una bajada real, conserva ambos precios y no duplica avisos al repetir la lectura', () => {
  const first = reconcilePriceAlerts(emptyPriceAlerts(), [game]);
  const drop = reconcilePriceAlerts(first, snapshot(15000), '2026-01-02T00:00:00Z');
  expect(drop.notifications).toHaveLength(1);
  expect(drop.notifications[0]).toMatchObject({ gameId: 'juego', previousPrice: 20000, price: 15000, currency: 'CLP', platform: 'PC', read: false });
  expect(reconcilePriceAlerts(drop, snapshot(15000)).notifications).toHaveLength(1);
});
it('no confunde monedas, tiendas o plataformas diferentes', () => {
  const first = reconcilePriceAlerts(emptyPriceAlerts(), [game]);
  for (const change of [{ moneda: 'USD' }, { tiendaId: 'otra' }, { plataforma: 'PS5' }]) {
    const state = reconcilePriceAlerts(first, [{ ...game, precios: [{ ...game.precios![0], precio: 1, ...change }] }]);
    expect(state.notifications).toEqual([]);
  }
});
it('no inventa una plataforma para ofertas antiguas y solo compara la misma tienda y moneda', () => {
  const unknown = [{ ...game, precios: [{ tiendaId: 'tienda', precio: 20000, moneda: 'CLP' }] }];
  const first = reconcilePriceAlerts(emptyPriceAlerts(), unknown);
  const drop = reconcilePriceAlerts(first, [{ ...game, precios: [{ tiendaId: 'tienda', precio: 15000, moneda: 'CLP' }] }]);
  expect(drop.notifications[0].platform).toBeUndefined();
  expect(reconcilePriceAlerts(first, snapshot(15000)).notifications).toEqual([]);
});
it('admite una bajada a cero y no anuncia aumentos ni precios inválidos', () => {
  const first = reconcilePriceAlerts(emptyPriceAlerts(), [game]);
  expect(reconcilePriceAlerts(first, snapshot(0)).notifications[0].price).toBe(0);
  expect(reconcilePriceAlerts(first, snapshot(30000)).notifications).toEqual([]);
  for (const price of [-1, Infinity, NaN]) expect(reconcilePriceAlerts(first, snapshot(price)).notifications).toEqual([]);
});
it('no genera avisos por asociaciones duplicadas y ambiguas', () => {
  const first = reconcilePriceAlerts(emptyPriceAlerts(), [game]);
  expect(reconcilePriceAlerts(first, [{ ...game, precios: [game.precios![0], { ...game.precios![0], precio: 1 }] }]).notifications).toEqual([]);
});
it('quita referencias al retirar un deseado y no anuncia una bajada al volver a agregarlo', () => {
  const first = reconcilePriceAlerts(emptyPriceAlerts(), [game]);
  const removed = reconcilePriceAlerts(first, []);
  expect(removed.prices).toEqual({});
  expect(reconcilePriceAlerts(removed, snapshot(10000)).notifications).toEqual([]);
});
it('restaura avisos leídos y rechaza datos corruptos, enlaces inseguros y falsos descuentos', () => {
  const first = reconcilePriceAlerts(emptyPriceAlerts(), [game]);
  const drop = reconcilePriceAlerts(first, snapshot(15000));
  drop.notifications[0].read = true;
  drop.notifications[0].url = 'javascript:alert(1)';
  const restored = parsePriceAlerts(JSON.stringify(drop));
  expect(restored.notifications[0].read).toBe(true);
  expect(restored.notifications[0].url).toBeUndefined();
  expect(parsePriceAlerts('incorrecto')).toEqual(emptyPriceAlerts());
  drop.notifications[0].price = 30000;
  expect(parsePriceAlerts(JSON.stringify(drop)).notifications).toEqual([]);
});
