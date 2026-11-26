import { useEffect, useRef, useState } from 'react';
import { fieldCls, panel } from './common';
import { ErrorState } from './Status';
import { errorMessage } from '../services/http';
import { gameDraft, gamePayload, loadAdminGame, requirementFields, saveAdminGame, splitList, type GameDraft } from '../services/adminGames';

export default function GameEditor({ gameId, onSaved }: { gameId?: string; onSaved: () => void }) {
  const [draft, setDraft] = useState<GameDraft>(() => gameDraft());
  const [original, setOriginal] = useState<GameDraft>();
  const [loading, setLoading] = useState(!!gameId), [saving, setSaving] = useState(false);
  const [error, setError] = useState(''), [retry, setRetry] = useState(0);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    const controller = new AbortController();
    setError(''); setOriginal(undefined);
    if (!gameId) { setDraft(gameDraft()); setLoading(false); return; }
    setLoading(true);
    loadAdminGame(gameId, controller.signal).then(game => {
      if (controller.signal.aborted) return;
      const loaded = gameDraft(game); setDraft(loaded); setOriginal(loaded); setLoading(false);
    }).catch(e => { if (!controller.signal.aborted) { setError(errorMessage(e)); setLoading(false); } });
    return () => controller.abort();
  }, [gameId, retry]);

  async function submit() {
    setError('');
    try {
      const payload = gamePayload(draft, original);
      setSaving(true);
      const saved = await saveAdminGame(payload, gameId);
      if (!mounted.current) return;
      const next = gameId ? gameDraft(saved) : gameDraft();
      setDraft(next); setOriginal(gameId ? next : undefined); onSaved();
    } catch (e) { if (mounted.current) setError(errorMessage(e)); }
    finally { if (mounted.current) setSaving(false); }
  }
  if (loading) return <p role="status" className="mt-5 text-sm text-slate-400">Cargando información del juego…</p>;
  if (gameId && !original) return <div className="mt-5"><ErrorState message={error || 'No se pudo cargar el juego.'} retry={() => setRetry(n => n + 1)} /></div>;
  const update = (key: keyof GameDraft, value: string | boolean) => setDraft(d => ({ ...d, [key]: value }));
  return <form aria-label="Información del videojuego" className={`${panel} mt-5`} onSubmit={e => { e.preventDefault(); if (!saving) void submit(); }}>
    <h2 className="text-lg font-bold">{gameId ? 'Editar información del juego' : 'Crear un juego'}</h2>
    <p className="mt-1 text-sm text-slate-400">Completa solo información verificada. Los campos opcionales pueden quedar vacíos.</p>
    {error && <div className="mt-4"><ErrorState message={error} /></div>}
    <fieldset disabled={saving} className="mt-5 space-y-6 disabled:opacity-60">
      <div className="grid gap-4 sm:grid-cols-2">
        {([['titulo', 'Título'], ['desarrollador', 'Desarrollador'], ['imagenPortada', 'URL de portada'],
          ['fechaLanzamiento', 'Fecha de lanzamiento'], ['generos', 'Géneros separados por coma'],
          ['plataformas', 'Plataformas separadas por coma']] as const).map(([key, label]) =>
          <label key={key} className="block text-sm">{label}<input required={key === 'titulo'}
            maxLength={key === 'imagenPortada' ? 2000 : ['generos', 'plataformas'].includes(key) ? 5000 : 200}
            type={key === 'fechaLanzamiento' ? 'date' : key === 'imagenPortada' ? 'url' : 'text'}
            value={draft[key]} onChange={e => update(key, e.target.value)} className={fieldCls} /></label>)}
        <label className="block text-sm sm:col-span-2">Resumen del encabezado<textarea rows={3} maxLength={600}
          value={draft.descripcionCorta} onChange={e => update('descripcionCorta', e.target.value)} className={fieldCls} />
          <span className="mt-1 block text-xs text-slate-400">Si está vacío, la ficha utiliza una vista breve de la descripción.</span></label>
        <label className="block text-sm sm:col-span-2">Descripción<textarea rows={6} maxLength={20000}
          value={draft.descripcion} onChange={e => update('descripcion', e.target.value)} className={fieldCls} /></label>
        <label className="block text-sm sm:col-span-2">Características del juego<textarea rows={4} maxLength={9030}
          aria-describedby="features-help" value={draft.caracteristicas} onChange={e => update('caracteristicas', e.target.value)} className={fieldCls} />
          <span id="features-help" className="mt-1 block text-xs text-slate-400">Una característica por línea; hasta 30, de 300 caracteres cada una. Se omiten líneas vacías y repetidas.</span></label>
      </div>
      <section aria-labelledby="requirements-heading" className="border-t border-blue-500/20 pt-5">
        <h3 id="requirements-heading" className="font-bold">Requisitos del sistema</h3>
        <p className="mt-1 text-sm text-slate-400">Selecciona la plataforma indicada por la fuente. Los mínimos y recomendados son independientes.</p>
        <label className="mt-4 block text-sm sm:max-w-sm">Plataforma de los requisitos<select value={draft.plataformaRequisitos}
          onChange={e => update('plataformaRequisitos', e.target.value)} className={fieldCls}>
          <option value="">Selecciona una plataforma</option>
          {splitList(draft.plataformas).map(p => <option key={p} value={p}>{p}</option>)}
          {draft.plataformaRequisitos && !splitList(draft.plataformas).includes(draft.plataformaRequisitos) &&
            <option value={draft.plataformaRequisitos}>{draft.plataformaRequisitos} (no incluida en el juego)</option>}
        </select></label>
        <div className="mt-4 grid gap-5 md:grid-cols-2">
          {(['minimos', 'recomendados'] as const).map(group => <fieldset key={group} className="space-y-3 rounded-lg border border-blue-500/20 p-4">
            <legend className="px-2 text-sm font-bold">{group === 'minimos' ? 'Mínimos' : 'Recomendados'}</legend>
            {requirementFields.map(([key, label]) => <label key={key} className="block text-sm">{label}
              <textarea rows={key === 'notas' ? 3 : 2} maxLength={key === 'notas' ? 2000 : 500}
                value={draft[group][key]} onChange={e => setDraft(d => ({ ...d, [group]: { ...d[group], [key]: e.target.value } }))}
                className={fieldCls} /></label>)}
          </fieldset>)}
        </div>
        <button type="button" onClick={() => setDraft(d => ({ ...d, plataformaRequisitos: '', minimos: gameDraft().minimos, recomendados: gameDraft().recomendados }))}
          className="mt-4 rounded-lg border border-blue-500/30 px-4 py-2 text-sm">Vaciar campos de requisitos</button>
        <p className="mt-2 text-xs text-slate-400">Vaciar los campos solo modifica este formulario. El cambio se aplica al presionar Guardar juego.</p>
      </section>
      <div className="flex flex-wrap items-center justify-between gap-4 border-t border-blue-500/20 pt-5">
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={draft.activo}
          onChange={e => update('activo', e.target.checked)} />Visible en el catálogo</label>
        <button disabled={saving} className="rounded-lg bg-blue-600 px-5 py-3 text-sm font-bold text-white hover:bg-blue-500 disabled:opacity-40">
          {saving ? 'Guardando…' : gameId ? 'Guardar juego' : 'Crear juego'}
        </button>
      </div>
    </fieldset>
  </form>;
}
