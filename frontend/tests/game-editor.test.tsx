import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GameEditor from '../src/components/GameEditor';
import { gameDraft, gamePayload, type EditableGame } from '../src/services/adminGames';

const stored: EditableGame = {
  _id: 'juego', titulo: 'Ficha sintética', descripcion: null, descripcionCorta: 'Resumen anterior',
  fechaLanzamiento: '2024-03-20T12:34:56Z', plataformas: ['PC', 'PS5'], generos: ['Aventura'],
  caracteristicas: ['Exploración de prueba'],
  requisitosSistema: { plataforma: 'PC', minimos: { procesador: 'CPU de prueba' }, recomendados: { memoria: 'Memoria de prueba' } },
};
const response = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status });
afterEach(() => vi.unstubAllGlobals());

describe('Conservación de datos al editar una ficha', () => {
  it('solo envía el campo editado y el título requerido, conservando fechas y nulos originales', () => {
    const original = gameDraft(stored);
    expect(gamePayload({ ...original, descripcionCorta: 'Nuevo resumen' }, original)).toEqual({
      titulo: stored.titulo, descripcionCorta: 'Nuevo resumen',
    });
    expect(gamePayload(original, original)).toEqual({ titulo: stored.titulo });
  });
  it('permite editar un título sin volver a escribir requisitos heredados sin plataforma', () => {
    const original = gameDraft({ ...stored, requisitosSistema: { minimos: { notas: 'Dato heredado' } } });
    expect(gamePayload({ ...original, titulo: 'Título corregido' }, original)).toEqual({ titulo: 'Título corregido' });
  });
  it('exige plataforma para nuevos requisitos y no copia los mínimos a recomendados', () => {
    const draft = gameDraft({ titulo: 'Nuevo', plataformas: ['PC'] });
    draft.minimos.memoria = 'Memoria de prueba';
    expect(() => gamePayload(draft)).toThrow('Selecciona una plataforma');
    draft.plataformaRequisitos = 'PC';
    const payload = JSON.parse(JSON.stringify(gamePayload(draft)));
    expect(payload.requisitosSistema).toEqual({ plataforma: 'PC', minimos: { memoria: 'Memoria de prueba' } });
    expect(payload.precios).toBeUndefined();
    expect(payload.imagenFondo).toBeUndefined();
  });
  it('impide retirar la plataforma de requisitos existentes', () => {
    const original = gameDraft(stored);
    expect(() => gamePayload({ ...original, plataformas: 'PS5' }, original)).toThrow('debe seguir incluida');
  });
});

describe('Editor administrativo de fichas', () => {
  it('carga el documento completo y guarda únicamente el resumen modificado', async () => {
    const onSaved = vi.fn();
    const fetcher = vi.fn(async (_path: string, init: RequestInit) => response(init.method === 'PUT'
      ? { ...stored, ...JSON.parse(init.body as string) } : stored));
    vi.stubGlobal('fetch', fetcher);
    const u = userEvent.setup();
    render(<GameEditor gameId="juego" onSaved={onSaved} />);
    expect(screen.getByRole('status').textContent).toContain('Cargando');
    const summary = await screen.findByLabelText('Resumen del encabezado', { exact: false });
    expect((screen.getByLabelText('Descripción', { exact: true }) as HTMLTextAreaElement).value).toBe('');
    expect(within(screen.getByRole('group', { name: 'Mínimos' })).getByLabelText('Procesador')).toHaveProperty('value', 'CPU de prueba');
    await u.clear(summary); await u.type(summary, 'Resumen actualizado');
    await u.click(screen.getByRole('button', { name: 'Guardar juego' }));
    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    const [path, init] = fetcher.mock.calls.find(([, init]) => init.method === 'PUT')!;
    expect(path).toContain('/juegos/juego');
    expect(JSON.parse(init.body as string)).toEqual({ titulo: stored.titulo, descripcionCorta: 'Resumen actualizado' });
  });
  it('crea una ficha con características y requisitos explícitos desde el formulario', async () => {
    const fetcher = vi.fn(async (_path: string, init: RequestInit) => response({ _id: 'nuevo', ...JSON.parse(init.body as string) }, 201));
    vi.stubGlobal('fetch', fetcher);
    const onSaved = vi.fn(), u = userEvent.setup();
    render(<GameEditor onSaved={onSaved} />);
    await u.type(screen.getByLabelText('Título'), 'Nueva ficha de prueba');
    await u.type(screen.getByLabelText('Plataformas separadas por coma'), 'PC, PS5');
    await u.type(screen.getByLabelText('Características del juego', { exact: false }), 'Exploración\nCooperativo\nExploración');
    await u.selectOptions(screen.getByLabelText('Plataforma de los requisitos'), 'PC');
    await u.type(within(screen.getByRole('group', { name: 'Mínimos' })).getByLabelText('Memoria'), 'Memoria sintética');
    await u.click(screen.getByRole('button', { name: 'Crear juego' }));
    await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
    const payload = JSON.parse(fetcher.mock.calls[0][1].body as string);
    expect(payload.caracteristicas).toEqual(['Exploración', 'Cooperativo']);
    expect(payload.requisitosSistema).toEqual({ plataforma: 'PC', minimos: { memoria: 'Memoria sintética' } });
    expect(payload.imagenPortada).toBeNull();
    expect(payload.precios).toBeUndefined();
  });
  it('vaciar requisitos no solicita cambios hasta guardar y conserva el resto del documento', async () => {
    const fetcher = vi.fn(async (_path: string, init: RequestInit) => response(init.method === 'PUT'
      ? { ...stored, ...JSON.parse(init.body as string) } : stored));
    vi.stubGlobal('fetch', fetcher);
    const u = userEvent.setup();
    render(<GameEditor gameId="juego" onSaved={vi.fn()} />);
    await screen.findByLabelText('Título');
    await u.click(screen.getByRole('button', { name: 'Vaciar campos de requisitos' }));
    expect(fetcher).toHaveBeenCalledTimes(1);
    await u.click(screen.getByRole('button', { name: 'Guardar juego' }));
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
    expect(JSON.parse(fetcher.mock.calls[1][1].body as string)).toEqual({ titulo: stored.titulo, requisitosSistema: null });
  });
  it('muestra errores del servidor sin anunciar éxito ni borrar el formulario', async () => {
    vi.stubGlobal('fetch', vi.fn(async (_path: string, init: RequestInit) => init.method === 'PUT'
      ? response({ detail: 'La información cambió; vuelve a cargarla' }, 409) : response(stored)));
    const onSaved = vi.fn(), u = userEvent.setup();
    render(<GameEditor gameId="juego" onSaved={onSaved} />);
    const title = await screen.findByLabelText('Título');
    await u.clear(title); await u.type(title, 'No se debe perder');
    await u.click(screen.getByRole('button', { name: 'Guardar juego' }));
    expect((await screen.findByRole('alert')).textContent).toContain('La información cambió');
    expect(title).toHaveProperty('value', 'No se debe perder');
    expect(onSaved).not.toHaveBeenCalled();
  });
  it('permite reintentar una carga fallida y no presenta un editor vacío como si estuviera listo', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response({ detail: 'No se pudo leer la ficha' }, 503))
      .mockResolvedValueOnce(response(stored));
    vi.stubGlobal('fetch', fetcher);
    const u = userEvent.setup();
    render(<GameEditor gameId="juego" onSaved={vi.fn()} />);
    expect((await screen.findByRole('alert')).textContent).toContain('No se pudo leer');
    expect(screen.queryByRole('button', { name: 'Guardar juego' })).toBeNull();
    await u.click(screen.getByRole('button', { name: 'Volver a intentar' }));
    expect(await screen.findByLabelText('Título')).toHaveProperty('value', stored.titulo);
  });
});
