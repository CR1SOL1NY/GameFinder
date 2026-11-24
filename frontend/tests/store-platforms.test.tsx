import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import StoreEditor from '../src/components/StoreEditor';
import OfferEditor from '../src/components/OfferEditor';
import { mapearJuego, type TiendaAPI } from '../src/api';
import { compatiblePlatforms, storePlatforms } from '../src/services/offers';

const stores: TiendaAPI[] = [
  { _id: 'pc', nombre: 'Tienda PC sintética', plataformas: ['PC'] },
  { _id: 'consolas', nombre: 'Tienda de consolas sintética', plataformas: ['PS5', 'Xbox'] },
  { _id: 'desconocida', nombre: 'Tienda antigua sintética' },
  { _id: 'otra', nombre: 'Tienda Switch sintética', plataformas: ['Nintendo Switch'] },
];
const game = mapearJuego({ _id: 'juego', titulo: 'Juego sintético', plataformas: ['PC', 'PS5'], precios: [] }, stores);
const response = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status });
afterEach(() => vi.unstubAllGlobals());

function fetchStore(result = stores[0], status = 200) {
  const fn = vi.fn(async (input: string, _init: RequestInit = {}) => input.includes('/juegos/filtros')
    ? response({ generos: [], plataformas: ['PC', 'PS5', 'Xbox'] }) : response(result, status));
  vi.stubGlobal('fetch', fn);
  return fn;
}

describe('Compatibilidad de plataformas', () => {
  it('calcula la intersección y distingue una tienda desconocida de una configurada', () => {
    expect(compatiblePlatforms(game.platforms, stores[0])).toEqual(['PC']);
    expect(compatiblePlatforms(game.platforms, stores[1])).toEqual(['PS5']);
    expect(compatiblePlatforms(game.platforms, stores[3])).toEqual([]);
    expect(compatiblePlatforms(game.platforms)).toEqual([]);
    expect(storePlatforms(stores[2])).toBeUndefined();
    // Compatibilidad de escritura heredada: no es una afirmación de soporte confirmado.
    expect(compatiblePlatforms(game.platforms, stores[2])).toEqual(['PC', 'PS5']);
  });

  it('ofrece solo plataformas comunes y limpia una selección al cambiar de tienda', async () => {
    const fetcher = fetchStore(), u = userEvent.setup();
    render(<OfferEditor game={game} stores={stores} onSaved={vi.fn()} />);
    await u.selectOptions(screen.getByLabelText('Tienda'), 'pc');
    const select = screen.getByLabelText('Plataforma de esta oferta');
    expect(within(select).getAllByRole('option').map(o => (o as HTMLOptionElement).value)).toEqual(['', 'PC']);
    await u.selectOptions(select, 'PC');
    await u.selectOptions(screen.getByLabelText('Tienda'), 'consolas');
    expect(select).toHaveProperty('value', '');
    expect(within(select).getAllByRole('option').map(o => (o as HTMLOptionElement).value)).toEqual(['', 'PS5']);
    expect(screen.getByRole('option', { name: /Tienda Switch sintética/ })).toHaveProperty('disabled', true);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it('advierte al usar una tienda sin configurar y no inventa su relación', async () => {
    const u = userEvent.setup();
    render(<OfferEditor game={game} stores={stores} onSaved={vi.fn()} />);
    await u.selectOptions(screen.getByLabelText('Tienda'), 'desconocida');
    expect(screen.getByText(/La tienda no tiene plataformas configuradas/)).toBeTruthy();
    expect(screen.getByLabelText('Plataforma de esta oferta')).toHaveProperty('value', '');
  });
});

describe('Configuración de plataformas de una tienda', () => {
  it('crea una tienda con varias plataformas explícitas sin escribir ofertas', async () => {
    const fetcher = fetchStore(), onSaved = vi.fn(), u = userEvent.setup();
    render(<StoreEditor stores={stores} onSaved={onSaved} />);
    await u.type(screen.getByLabelText('Nombre'), 'Nueva tienda sintética');
    await u.click(screen.getByLabelText('Configurar plataformas de esta tienda'));
    for (const value of ['PC', 'PS5', 'PC']) {
      await u.type(screen.getByLabelText('Añadir plataforma'), value);
      await u.click(screen.getByRole('button', { name: 'Añadir plataforma', exact: true }));
    }
    expect(within(screen.getByRole('list', { name: 'Plataformas de la tienda' })).getAllByRole('listitem')).toHaveLength(2);
    await u.click(screen.getByRole('button', { name: 'Guardar tienda' }));
    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    const [path, init] = fetcher.mock.calls.find(([, init]) => init.method === 'POST')!;
    expect(path).toContain('/tiendas/');
    expect(JSON.parse(init.body as string)).toEqual({ nombre: 'Nueva tienda sintética', url_base: null, plataformas: ['PC', 'PS5'] });
  });

  it('editar el nombre no borra ni reenvía plataformas ya configuradas', async () => {
    const fetcher = fetchStore(), u = userEvent.setup();
    render(<StoreEditor stores={stores} onSaved={vi.fn()} />);
    await u.selectOptions(screen.getByLabelText('Tienda'), 'pc');
    const name = screen.getByLabelText('Nombre');
    await u.clear(name); await u.type(name, 'Nombre corregido');
    await u.click(screen.getByRole('button', { name: 'Guardar tienda' }));
    await waitFor(() => expect(fetcher.mock.calls.some(([, init]) => init.method === 'PUT')).toBe(true));
    expect(JSON.parse(fetcher.mock.calls.find(([, init]) => init.method === 'PUT')![1].body as string)).toEqual({ nombre: 'Nombre corregido' });
  });

  it('quitar la configuración es explícito y no modifica documentos de juegos', async () => {
    const fetcher = fetchStore({ ...stores[0], plataformas: null }), u = userEvent.setup();
    render(<StoreEditor stores={stores} onSaved={vi.fn()} />);
    await u.selectOptions(screen.getByLabelText('Tienda'), 'pc');
    await u.click(screen.getByLabelText('Configurar plataformas de esta tienda'));
    await u.click(screen.getByRole('button', { name: 'Guardar tienda' }));
    await waitFor(() => expect(fetcher.mock.calls.some(([, init]) => init.method === 'PUT')).toBe(true));
    const [path, init] = fetcher.mock.calls.find(([, init]) => init.method === 'PUT')!;
    expect(path).toContain('/tiendas/pc');
    expect(JSON.parse(init.body as string)).toEqual({ nombre: stores[0].nombre, plataformas: null });
  });

  it('evita guardar una configuración vacía o texto de plataforma sin añadir', async () => {
    const fetcher = fetchStore(), u = userEvent.setup();
    render(<StoreEditor stores={stores} onSaved={vi.fn()} />);
    await u.selectOptions(screen.getByLabelText('Tienda'), 'pc');
    await u.click(screen.getByRole('button', { name: 'Quitar PC' }));
    await u.click(screen.getByRole('button', { name: 'Guardar tienda' }));
    expect((await screen.findByRole('alert')).textContent).toContain('al menos una plataforma');
    await u.type(screen.getByLabelText('Añadir plataforma'), 'PS5');
    await u.click(screen.getByRole('button', { name: 'Guardar tienda' }));
    expect(screen.getByRole('alert').textContent).toContain('Añade la plataforma escrita');
    expect(fetcher.mock.calls.some(([, init]) => init.method === 'PUT')).toBe(false);
  });

  it('un conflicto con ofertas existentes conserva la configuración y no anuncia éxito', async () => {
    const fetcher = vi.fn(async (path: string, _init: RequestInit = {}) => path.includes('/juegos/filtros')
      ? response({ plataformas: ['PC', 'PS5'] }) : response({ detail: 'La tienda tiene ofertas en otras plataformas' }, 409));
    vi.stubGlobal('fetch', fetcher);
    const onSaved = vi.fn(), u = userEvent.setup();
    render(<StoreEditor stores={stores} onSaved={onSaved} />);
    await u.selectOptions(screen.getByLabelText('Tienda'), 'consolas');
    await u.click(screen.getByRole('button', { name: 'Quitar PS5' }));
    await u.click(screen.getByRole('button', { name: 'Guardar tienda' }));
    expect((await screen.findByRole('alert')).textContent).toContain('ofertas en otras plataformas');
    expect(screen.getByRole('button', { name: 'Quitar Xbox' })).toBeTruthy();
    expect(onSaved).not.toHaveBeenCalled();
  });
});
