import { beforeEach, describe, it, expect, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { parseComparisons, recordComparison, useComparisonHistory } from '../src/services/comparisons';

beforeEach(() => localStorage.clear());

describe('Actividad real de comparación guardada por cuenta', () => {
  it('ordena los últimos juegos distintos y repetir uno no infla el contador', () => {
    recordComparison('ana', 'a', '2026-01-01T00:00:00Z');
    recordComparison('ana', 'b', '2026-01-02T00:00:00Z');
    recordComparison('ana', 'a', '2026-01-03T00:00:00Z');
    const { result } = renderHook(() => useComparisonHistory('ana'));
    expect(result.current.entries).toEqual([{ gameId: 'a', comparedAt: '2026-01-03T00:00:00Z' }, { gameId: 'b', comparedAt: '2026-01-02T00:00:00Z' }]);
  });
  it('no mezcla cuentas y persiste al volver a cargar el componente', () => {
    recordComparison('ana', 'privado-ana');
    const { result, rerender, unmount } = renderHook(({ user }) => useComparisonHistory(user), { initialProps: { user: 'ana' } });
    expect(result.current.entries[0].gameId).toBe('privado-ana');
    rerender({ user: 'otra' });
    expect(result.current.entries).toEqual([]);
    unmount();
    expect(renderHook(() => useComparisonHistory('ana')).result.current.entries).toHaveLength(1);
  });
  it('actualiza la vista al comparar y al recibir cambios desde otra pestaña', () => {
    const { result } = renderHook(() => useComparisonHistory('ana'));
    act(() => { recordComparison('ana', 'a'); });
    expect(result.current.entries).toHaveLength(1);
    act(() => {
      localStorage.removeItem('gf-comparisons-v1:ana');
      window.dispatchEvent(new StorageEvent('storage', { key: 'gf-comparisons-v1:ana' }));
    });
    expect(result.current.entries).toEqual([]);
  });
  it('ignora datos corruptos y no guarda correos, tokens o datos del videojuego', () => {
    expect(parseComparisons('no-json')).toEqual([]);
    expect(parseComparisons(JSON.stringify([null, {}, { gameId: 'a', comparedAt: 'fecha inválida' }]))).toEqual([]);
    expect(parseComparisons(JSON.stringify([{ gameId: 'a', comparedAt: '2026-01-01', token: 'no-conservar', correo: 'no-conservar' }]))).toEqual([{ gameId: 'a', comparedAt: '2026-01-01' }]);
  });
  it('maneja almacenamiento bloqueado y no inventa un historial guardado', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new DOMException('Bloqueado', 'SecurityError'); });
    expect(recordComparison('ana', 'a')).toBe(false);
    const { result } = renderHook(() => useComparisonHistory('ana'));
    expect(result.current.available).toBe(false);
    expect(result.current.entries).toEqual([]);
  });
  it('limita el almacenamiento a los 500 juegos distintos más recientes', () => {
    const data = Array.from({ length: 501 }, (_, i) => ({ gameId: String(i), comparedAt: new Date(2026, 0, 1, 0, i).toISOString() }));
    const parsed = parseComparisons(JSON.stringify(data));
    expect(parsed).toHaveLength(500);
    expect(parsed[0].gameId).toBe('500');
    expect(parsed.at(-1)?.gameId).toBe('1');
  });
});
