import { afterEach, describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import OfferEditor from '../src/components/OfferEditor';
import { mapearJuego } from '../src/api';
import { offerPath, saveOffer } from '../src/services/offers';
import { type StoreOffer } from '../src/games';

const offer: StoreOffer = { storeId: 'tienda', name: 'Tienda de prueba', price: 20000, currency: 'CLP', platform: 'PC' };
const draft = { tiendaId: 'tienda', precio: 20000, moneda: 'CLP', plataforma: 'PC', urlProducto: null };
afterEach(() => vi.unstubAllGlobals());

function fetchOk() {
  const fetcher = vi.fn(async (_input: string, _init: RequestInit) => new Response(JSON.stringify({ mensaje: 'Ofertas actualizadas' }), { status: 200 }));
  vi.stubGlobal('fetch', fetcher);
  return fetcher;
}

describe('Identificación y escritura de ofertas', () => {
  it('conserva el identificador recibido de FastAPI', () => {
    const game = mapearJuego({ _id: 'juego', titulo: 'Prueba', precios: [{ ofertaId: 'oferta', tiendaId: 'tienda', precio: 20000, plataforma: 'PC', moneda: 'CLP' }] }, []);
    expect(game.offers[0].id).toBe('oferta');
    expect(offerPath('juego', game.offers[0])).toBe('/juegos/juego/ofertas/oferta');
  });
  it('selecciona ofertas antiguas usando plataforma y moneda', () => {
    const path = new URL(offerPath('juego', offer), 'https://example.com');
    expect(path.pathname).toBe('/juegos/juego/tiendas/tienda');
    expect(path.searchParams.get('moneda')).toBe('CLP');
    expect(path.searchParams.get('plataforma')).toBe('PC');
    expect(path.searchParams.has('sin_plataforma')).toBe(false);
  });
  it('distingue una plataforma ausente de todas las plataformas', () => {
    const query = new URL(offerPath('juego', { ...offer, platform: undefined }), 'https://example.com').searchParams;
    expect(query.get('sin_plataforma')).toBe('true');
    expect(query.get('moneda')).toBe('CLP');
    expect(query.has('plataforma')).toBe(false);
  });
  it('crea una oferta con su plataforma declarada', async () => {
    const fetcher = fetchOk();
    await saveOffer('juego', draft);
    expect(fetcher.mock.calls[0][0]).toBe('http://127.0.0.1:8001/juegos/juego/ofertas');
    expect(JSON.parse(fetcher.mock.calls[0][1].body as string)).toEqual(draft);
  });
  it('clasifica sin reenviar ni cambiar el precio', async () => {
    const fetcher = fetchOk();
    await saveOffer('juego', draft, { ...offer, platform: undefined });
    const [path, init] = fetcher.mock.calls[0];
    expect(String(path)).toContain('sin_plataforma=true');
    expect(JSON.parse(init.body as string)).toEqual({ plataforma: 'PC' });
  });
  it('edita solo el precio de la oferta identificada', async () => {
    const fetcher = fetchOk();
    await saveOffer('juego', { ...draft, precio: 21000 }, { ...offer, id: 'oferta-pc' });
    expect(fetcher.mock.calls[0][0]).toBe('http://127.0.0.1:8001/juegos/juego/ofertas/oferta-pc');
    expect(JSON.parse(fetcher.mock.calls[0][1].body as string)).toEqual({ precio: 21000 });
  });
});

describe('Formulario administrativo', () => {
  const game = mapearJuego({ _id: 'juego', titulo: 'Prueba sintética', plataformas: ['PC', 'PS5'], precios: [{ ofertaId: 'oferta-pc', tiendaId: 'tienda', precio: 20000, moneda: 'CLP', plataforma: 'PC' }, { ofertaId: 'oferta-ps5', tiendaId: 'tienda', precio: 30000, moneda: 'CLP', plataforma: 'PS5' }] }, [{ _id: 'tienda', nombre: 'Tienda de prueba' }]);
  it('permite editar el precio de PS5 independientemente del precio de PC', async () => {
    const fetcher = fetchOk();
    const onSaved = vi.fn();
    const u = userEvent.setup();
    render(<OfferEditor game={game} stores={[{ _id: 'tienda', nombre: 'Tienda de prueba' }]} onSaved={onSaved} />);
    await u.selectOptions(screen.getByLabelText('Oferta'), '1');
    expect((screen.getByLabelText('Plataforma de esta oferta') as HTMLSelectElement).value).toBe('PS5');
    await u.clear(screen.getByLabelText('Precio'));
    await u.type(screen.getByLabelText('Precio'), '25000');
    await u.click(screen.getByRole('button', { name: 'Guardar cambios de esta oferta' }));
    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    expect(fetcher.mock.calls[0][0]).toContain('/ofertas/oferta-ps5');
    expect(JSON.parse(fetcher.mock.calls[0][1].body as string)).toEqual({ precio: 25000 });
  });
  it('no anuncia éxito cuando el backend rechaza una oferta duplicada', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ detail: 'Ya existe una oferta de esta tienda, plataforma y moneda' }), { status: 409 })));
    const onSaved = vi.fn();
    const u = userEvent.setup();
    render(<OfferEditor game={game} stores={[{ _id: 'tienda', nombre: 'Tienda de prueba' }]} onSaved={onSaved} />);
    await u.selectOptions(screen.getByLabelText('Oferta'), '1');
    await u.selectOptions(screen.getByLabelText('Plataforma de esta oferta'), 'PC');
    await u.click(screen.getByRole('button', { name: 'Guardar cambios de esta oferta' }));
    expect((await screen.findByRole('alert')).textContent).toContain('Ya existe una oferta');
    expect(onSaved).not.toHaveBeenCalled();
  });
  it('exige una plataforma al crear y no envía un formulario incompleto', async () => {
    const fetcher = fetchOk();
    const u = userEvent.setup();
    render(<OfferEditor game={game} stores={[{ _id: 'tienda', nombre: 'Tienda de prueba' }]} onSaved={vi.fn()} />);
    await u.selectOptions(screen.getByLabelText('Tienda'), 'tienda');
    await u.type(screen.getByLabelText('Precio'), '19000');
    await u.click(screen.getByRole('button', { name: 'Crear oferta para esta plataforma' }));
    expect(fetcher).not.toHaveBeenCalled();
  });
});
