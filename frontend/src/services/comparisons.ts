/** Historial local por cuenta. No escribe en MongoDB ni contiene tokens o correos. */
import { useMemo, useSyncExternalStore } from 'react';

export type Comparison = { gameId: string; comparedAt: string };
const eventName = 'gamefinder-comparison';
const unavailable = '!storage-unavailable';
const maxGames = 500;
const keyFor = (userId: string) => `gf-comparisons-v1:${userId}`;

export function parseComparisons(raw: string | null): Comparison[] {
  try {
    const data: unknown = JSON.parse(raw || '[]');
    if (!Array.isArray(data)) return [];
    const seen = new Set<string>();
    return data.filter((item): item is Comparison => !!item && typeof item.gameId === 'string' && item.gameId.length > 0 && item.gameId.length <= 200 && typeof item.comparedAt === 'string' && Number.isFinite(Date.parse(item.comparedAt)))
      .sort((a, b) => Date.parse(b.comparedAt) - Date.parse(a.comparedAt))
      .filter(item => { if (seen.has(item.gameId)) return false; seen.add(item.gameId); return true; })
      .slice(0, maxGames).map(({ gameId, comparedAt }) => ({ gameId, comparedAt }));
  } catch { return []; }
}

export function recordComparison(userId: string, gameId: string, now = new Date().toISOString()): boolean {
  if (!userId || !gameId) return false;
  try {
    const key = keyFor(userId);
    const previous = parseComparisons(localStorage.getItem(key));
    const next = parseComparisons(JSON.stringify([{ gameId, comparedAt: now }, ...previous.filter(row => row.gameId !== gameId)]));
    localStorage.setItem(key, JSON.stringify(next));
    window.dispatchEvent(new CustomEvent(eventName, { detail: key }));
    return true;
  } catch { return false; }
}

export function useComparisonHistory(userId: string) {
  const key = keyFor(userId);
  function subscribe(callback: () => void) {
    const onStorage = (event: StorageEvent) => { if (event.key === key || event.key === null) callback(); };
    const onLocal = (event: Event) => { if ((event as CustomEvent).detail === key) callback(); };
    window.addEventListener('storage', onStorage);
    window.addEventListener(eventName, onLocal);
    return () => { window.removeEventListener('storage', onStorage); window.removeEventListener(eventName, onLocal); };
  }
  function snapshot() {
    try { return localStorage.getItem(key); } catch { return unavailable; }
  }
  const raw = useSyncExternalStore(subscribe, snapshot, () => null);
  const entries = useMemo(() => parseComparisons(raw), [raw]);
  return { entries, available: raw !== unavailable };
}
