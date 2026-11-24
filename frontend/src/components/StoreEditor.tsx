import { useEffect, useState } from 'react';
import { obtenerFiltros, type TiendaAPI } from '../api';
import { request, jsonBody, errorMessage } from '../services/http';
import { storePlatforms } from '../services/offers';
import { ErrorState } from './Status';
import { panel, fieldCls } from './common';

export default function StoreEditor({ stores, onSaved }: { stores: TiendaAPI[]; onSaved: () => void }) {
  const [id, setId] = useState(''), [name, setName] = useState(''), [url, setUrl] = useState('');
  const [configured, setConfigured] = useState(false), [platforms, setPlatforms] = useState<string[]>([]);
  const [platform, setPlatform] = useState(''), [suggestions, setSuggestions] = useState<string[]>([]);
  const [suggestionsError, setSuggestionsError] = useState(false);
  const [original, setOriginal] = useState<TiendaAPI>();
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  useEffect(() => {
    const c = new AbortController();
    obtenerFiltros(c.signal).then(data => { if (!c.signal.aborted) setSuggestions(data.plataformas); })
      .catch(() => { if (!c.signal.aborted) setSuggestionsError(true); });
    return () => c.abort();
  }, []);
  function select(store?: TiendaAPI) {
    setId(store?._id || ''); setName(store?.nombre || ''); setUrl(store?.url_base || '');
    const supported = storePlatforms(store);
    setConfigured(!!supported); setPlatforms(supported || []); setPlatform(''); setOriginal(store); setError('');
  }
  function addPlatform() {
    const entered = platform.trim();
    if (!entered) return;
    const canonical = suggestions.find(p => p.toLocaleLowerCase('es') === entered.toLocaleLowerCase('es')) || entered;
    setPlatforms(previous => previous.some(p => p.toLocaleLowerCase('es') === canonical.toLocaleLowerCase('es')) ? previous : [...previous, canonical]);
    setPlatform(''); setError('');
  }
  async function save() {
    setError('');
    if (configured && platform.trim()) { setError('Añade la plataforma escrita antes de guardar la tienda.'); return; }
    if (configured && !platforms.length) { setError('Selecciona al menos una plataforma o deja la tienda sin configurar.'); return; }
    if (platforms.length > 50) { setError('Puedes registrar hasta 50 plataformas por tienda.'); return; }
    const payload: { nombre: string; url_base?: string | null; plataformas?: string[] | null } = { nombre: name.trim() };
    if (!original || url !== (original.url_base || '')) payload.url_base = url.trim() || null;
    const supported = storePlatforms(original);
    if (!original || configured !== !!supported || (configured && JSON.stringify(platforms) !== JSON.stringify(supported))) {
      payload.plataformas = configured ? platforms : null;
    }
    setBusy(true);
    try {
      const saved = await request<TiendaAPI>(id ? `/tiendas/${encodeURIComponent(id)}` : '/tiendas/', jsonBody(id ? 'PUT' : 'POST', payload));
      select(id ? saved : undefined); onSaved();
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  return <form aria-label="Configuración de tienda" className={`${panel} space-y-5`} onSubmit={e => { e.preventDefault(); if (!busy) void save(); }}>
    <h2 className="text-lg font-bold">Tiendas y plataformas</h2>
    {error && <ErrorState message={error} />}
    <fieldset disabled={busy} className="space-y-4 disabled:opacity-60">
      <label className="block text-sm">Tienda<select value={id} onChange={e => select(stores.find(s => s._id === e.target.value))} className={fieldCls}>
        <option value="">Crear tienda nueva</option>
        {stores.map(s => <option key={s._id} value={s._id}>{s.nombre}</option>)}
      </select></label>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-sm">Nombre<input required maxLength={100} value={name} onChange={e => setName(e.target.value)} className={fieldCls} /></label>
        <label className="block text-sm">URL principal<input type="url" maxLength={2000} value={url} onChange={e => setUrl(e.target.value)} className={fieldCls} /></label>
      </div>
      <fieldset className="rounded-lg border border-blue-500/20 p-4">
        <legend className="px-2 text-sm font-bold">Plataformas que vende la tienda</legend>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={configured} onChange={e => setConfigured(e.target.checked)} />Configurar plataformas de esta tienda</label>
        <p className="mt-2 text-xs text-slate-400">Marca solo plataformas confirmadas. Usa nombres específicos como PS4 y PS5, según el catálogo.</p>
        {configured ? <>
          <div className="mt-4 flex flex-col items-start gap-2 sm:flex-row sm:items-end">
            <label className="w-full text-sm sm:flex-1">Añadir plataforma<input value={platform} maxLength={100} list="store-platform-suggestions"
              onChange={e => setPlatform(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addPlatform(); } }} className={fieldCls} />
              <datalist id="store-platform-suggestions">{[...new Set([...suggestions, ...stores.flatMap(s => storePlatforms(s) || [])])].sort().map(p => <option key={p} value={p} />)}</datalist>
            </label>
            <button type="button" disabled={!platform.trim() || platforms.length >= 50} onClick={addPlatform} className="rounded-lg border border-blue-500/40 px-4 py-2.5 text-sm disabled:opacity-40">Añadir plataforma</button>
          </div>
          {suggestionsError && <p className="mt-2 text-xs text-amber-300">No se pudieron cargar las sugerencias. Puedes escribir el nombre exacto de la plataforma manualmente.</p>}
          <ul aria-label="Plataformas de la tienda" className="mt-4 flex flex-wrap gap-2">
            {platforms.map(p => <li key={p} className="flex max-w-full items-center gap-2 rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-2 text-sm">
              <span className="break-words">{p}</span><button type="button" aria-label={`Quitar ${p}`} onClick={() => setPlatforms(previous => previous.filter(value => value !== p))} className="rounded px-1 hover:bg-blue-500/20">×</button>
            </li>)}
          </ul>
          {!platforms.length && <p className="mt-3 text-sm text-slate-400">Añade al menos una plataforma confirmada.</p>}
        </> : <p className="mt-3 text-sm text-amber-300">Sin configurar: todavía no se sabe qué plataformas vende esta tienda. No se asignan a sus ofertas automáticamente.</p>}
      </fieldset>
      <p className="text-xs text-slate-400">Guardar plataformas no cambia precios ni clasifica ofertas antiguas. Si hay ofertas en otras plataformas, primero debes revisarlas en Ofertas.</p>
      <button disabled={busy} className="rounded-lg bg-blue-600 px-5 py-3 text-sm font-bold text-white disabled:opacity-40">{busy ? 'Guardando…' : 'Guardar tienda'}</button>
    </fieldset>
  </form>;
}
