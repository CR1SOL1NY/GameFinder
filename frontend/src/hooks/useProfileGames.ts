import { useEffect, useState } from 'react';
import { obtenerJuego } from '../api';
import { type Game } from '../games';
import { ApiError, errorMessage } from '../services/http';

/** Solo pide los juegos visibles y comparte resultados de deseos/actividad en el resumen. */
export function useProfileGames(ids: string[]) {
  const key = JSON.stringify([...new Set(ids)]);
  const [state, setState] = useState<{ key: string; games: Map<string, Game>; error: string; loading: boolean }>({ key: '', games: new Map(), error: '', loading: true });
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const current: string[] = JSON.parse(key);
    setState({ key, games: new Map(), error: '', loading: true });
    void Promise.allSettled(current.map(id => obtenerJuego(id, controller.signal))).then(results => {
      if (controller.signal.aborted) return;
      const games = new Map<string, Game>();
      let error = '';
      results.forEach(result => {
        if (result.status === 'fulfilled') games.set(result.value.id, result.value);
        else if (!(result.reason instanceof ApiError && result.reason.status === 404)) error = errorMessage(result.reason);
      });
      setState({ key, games, error, loading: false });
    });
    return () => controller.abort();
  }, [key, retry]);
  return { ...(state.key === key ? state : { games: new Map<string, Game>(), error: '', loading: true }), retry: () => setRetry(n => n + 1) };
}
