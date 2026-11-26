import { describe, it, expect } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import OfferComparison from '../src/components/OfferComparison';
import type { Game } from '../src/games';

const game: Game = {
  id: 'fixture-platforms', title: 'Juego de prueba', genres: [], platforms: ['PC', 'PS5', 'Xbox'],
  description: 'Fixture sintético, no datos de producción', price: 1000, rating: 0, reviews: 0,
  offers: [
    { storeId: 'steam', name: 'Steam de prueba', price: 19000, currency: 'CLP', platform: 'PC', url: 'https://example.com/pc' },
    { storeId: 'console', name: 'Tienda PS5 de prueba', price: 22000, currency: 'CLP', platform: 'PS5' },
    { storeId: 'epic', name: 'Epic de prueba', price: 17000, currency: 'CLP', platform: 'PC' },
    { storeId: 'unknown', name: 'Tienda sin plataforma', price: 1000, currency: 'CLP' },
    { storeId: 'usd', name: 'Tienda USD de prueba', price: 1, currency: 'USD', platform: 'PC' },
  ],
};
const selectPlatform = (name: string) => fireEvent.click(screen.getByRole('radio', { name }));
const table = () => within(screen.getByRole('table'));

describe('Comparación por plataforma', () => {
  it('elige una plataforma con precios y excluye las demás y las no informadas', () => {
    render(<OfferComparison game={game} />);
    expect((screen.getByRole('radio', { name: 'PC' }) as HTMLInputElement).checked).toBe(true);
    expect(table().getByText('Steam de prueba')).toBeTruthy();
    expect(table().getByText('Epic de prueba')).toBeTruthy();
    expect(table().queryByText('Tienda PS5 de prueba')).toBeNull();
    expect(table().queryByText('Tienda sin plataforma')).toBeNull();
    expect(table().queryByText('Tienda USD de prueba')).toBeNull();
    const best = table().getByText('Más barato').closest('tr')!;
    expect(within(best).getByText('Epic de prueba')).toBeTruthy();
  });

  it('al elegir PS5 muestra y calcula el mínimo solo de esa plataforma', () => {
    render(<OfferComparison game={game} />);
    selectPlatform('PS5');
    expect(screen.getByRole('heading', { name: 'Precios para PS5' })).toBeTruthy();
    expect(table().getByText('Tienda PS5 de prueba')).toBeTruthy();
    expect(table().queryByText('Steam de prueba')).toBeNull();
    expect(table().queryByText('Tienda sin plataforma')).toBeNull();
    expect(table().getAllByRole('row')).toHaveLength(2);
    expect(within(table().getByText('Más barato').closest('tr')!).getByText('Tienda PS5 de prueba')).toBeTruthy();
  });

  it('mantiene separadas las monedas y conserva la plataforma seleccionada', () => {
    render(<OfferComparison game={game} />);
    selectPlatform('PS5');
    fireEvent.change(screen.getByLabelText('Moneda'), { target: { value: 'USD' } });
    expect((screen.getByRole('radio', { name: 'PS5' }) as HTMLInputElement).checked).toBe(true);
    expect(screen.getByRole('heading', { name: 'Sin ofertas para PS5' })).toBeTruthy();
    expect(screen.queryByRole('table')).toBeNull();
    selectPlatform('PC');
    expect(table().getByText('Tienda USD de prueba')).toBeTruthy();
    expect(table().queryByText('Steam de prueba')).toBeNull();
    expect(screen.queryByRole('radio', { name: /Sin plataforma informada/ })).toBeNull();
  });

  it('una plataforma sin ofertas no hereda los precios de otras', () => {
    render(<OfferComparison game={game} />);
    selectPlatform('Xbox');
    expect(screen.getByRole('heading', { name: 'Sin ofertas para Xbox' })).toBeTruthy();
    expect(screen.queryByRole('table')).toBeNull();
    expect(screen.queryByText('Más barato')).toBeNull();
    expect(screen.queryByRole('link')).toBeNull();
  });

  it('muestra las ofertas no clasificadas aparte y no las declara mejores para una plataforma', () => {
    render(<OfferComparison game={game} />);
    fireEvent.click(screen.getByRole('radio', { name: 'Sin plataforma informada (1)' }));
    expect(table().getByText('Tienda sin plataforma')).toBeTruthy();
    expect(table().queryByText('Steam de prueba')).toBeNull();
    expect(screen.queryByText('Más barato')).toBeNull();
  });

  it('no supone que una oferta de Steam es de PC cuando falta la relación', () => {
    render(<OfferComparison game={{ ...game, offers: [{ storeId: 'steam', name: 'Steam', price: 19990, currency: 'CLP' }] }} />);
    expect(table().getByText('Steam')).toBeTruthy();
    selectPlatform('PC');
    expect(screen.getByRole('heading', { name: 'Sin ofertas para PC' })).toBeTruthy();
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('admite un precio cero confirmado y no crea un enlace cuando falta la URL', () => {
    render(<OfferComparison game={{ ...game, offers: [{ storeId: 'free', name: 'Prueba gratis', price: 0, currency: 'CLP', platform: 'PC' }] }} />);
    expect(table().getByText('Más barato')).toBeTruthy();
    expect(table().queryByText('Precio no disponible')).toBeNull();
    expect(table().getByText('Sin enlace')).toBeTruthy();
    expect(screen.queryByRole('link')).toBeNull();
  });

  it('no calcula un mejor precio cuando la moneda no está informada', () => {
    render(<OfferComparison game={{ ...game, offers: [{ storeId: 'one', name: 'Prueba', price: 20, currency: 'Sin moneda', platform: 'PC' }] }} />);
    expect(screen.queryByText('Más barato')).toBeNull();
    expect(screen.getByText(/no se calcula un precio mínimo/)).toBeTruthy();
  });

  it('permite seleccionar las plataformas del juego aun si no hay ofertas', () => {
    render(<OfferComparison game={{ ...game, offers: [] }} />);
    expect(screen.getByRole('group', { name: 'Selecciona tu plataforma' })).toBeTruthy();
    selectPlatform('PS5');
    expect(screen.getByRole('heading', { name: 'Sin ofertas para PS5' })).toBeTruthy();
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('restablece la selección al recibir otro juego y respeta sus plataformas reales', () => {
    const view = render(<OfferComparison game={game} />);
    selectPlatform('PS5');
    view.rerender(<OfferComparison game={{ ...game, id: 'otro-juego', platforms: ['Switch'], offers: [{ storeId: 'n', name: 'Tienda Switch', price: 10000, currency: 'CLP', platform: 'Switch' }] }} />);
    expect((screen.getByRole('radio', { name: 'Switch' }) as HTMLInputElement).checked).toBe(true);
    expect(table().getByText('Tienda Switch')).toBeTruthy();
    expect(screen.queryByRole('radio', { name: 'PS5' })).toBeNull();
  });
});
