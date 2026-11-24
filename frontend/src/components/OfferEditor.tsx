import { useState } from 'react';
import { type TiendaAPI } from '../api';
import { type Game, money } from '../games';
import { errorMessage } from '../services/http';
import { compatiblePlatforms, saveOffer, storePlatforms } from '../services/offers';
import { ErrorState } from './Status';
import { panel, fieldCls } from './common';

export default function OfferEditor({ game, stores, onSaved }: { game: Game; stores: TiendaAPI[]; onSaved: () => void }) {
  const [editing, setEditing] = useState<number | null>(null);
  const [store, setStore] = useState('');
  const [price, setPrice] = useState('');
  const [currency, setCurrency] = useState('CLP');
  const [platform, setPlatform] = useState('');
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const existing = editing === null ? undefined : game.offers[editing];
  const selectedStore = stores.find(item => item._id === store);
  const platforms = compatiblePlatforms(game.platforms, selectedStore);

  function select(value: string) {
    const index = value === '' ? null : Number(value);
    const offer = index === null ? undefined : game.offers[index];
    setEditing(index);
    setStore(offer?.storeId || '');
    setPrice(offer ? String(offer.price) : '');
    setCurrency(offer?.currency || 'CLP');
    setPlatform(offer?.platform || '');
    setUrl(offer?.url || '');
    setError('');
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      if (!selectedStore || !platforms.includes(platform)) throw new Error('Selecciona una plataforma compatible con el juego y la tienda.');
      await saveOffer(game.id, { tiendaId: store, precio: Number(price), moneda: currency, plataforma: platform, urlProducto: url || null }, existing);
      onSaved();
    } catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }

  return (
    <form className={`${panel} mt-5 grid gap-4 sm:grid-cols-2`} onSubmit={event => void submit(event)}>
      <div className="sm:col-span-2">
        <h2 className="font-bold">Precios por plataforma</h2>
        <p className="mt-2 text-sm text-slate-400">Registra una oferta por tienda, plataforma y moneda. Una misma tienda puede tener precios distintos para PC, PlayStation o Xbox.</p>
        <p className="mt-2 text-xs text-slate-400">Para completar una oferta antigua, selecciónala y confirma su plataforma en la tienda. Las demás ofertas conservarán sus precios.</p>
      </div>
      {error && <div className="sm:col-span-2"><ErrorState message={error} /></div>}
      <fieldset disabled={busy} className="contents">
        <label className="block text-sm sm:col-span-2">Oferta
          <select value={editing ?? ''} onChange={event => select(event.target.value)} className={fieldCls}>
            <option value="">Crear nueva oferta</option>
            {game.offers.map((offer, index) => <option value={index} key={offer.id || index}>{offer.name} · {offer.platform || 'Plataforma no informada'} · {money(offer.price, offer.currency)} {offer.currency}</option>)}
          </select>
        </label>
        <label className="block text-sm">Tienda
          <select required disabled={editing !== null} value={store} onChange={event => {
            const value = event.target.value;
            setStore(value);
            if (!compatiblePlatforms(game.platforms, stores.find(item => item._id === value)).includes(platform)) setPlatform('');
          }} className={fieldCls}>
            <option value="">Selecciona una tienda</option>
            {stores.map(item => <option key={item._id} value={item._id} disabled={!compatiblePlatforms(game.platforms, item).length}>{item.nombre}{!compatiblePlatforms(game.platforms, item).length ? ' (sin plataformas compatibles)' : ''}</option>)}
            {store && !selectedStore && <option value={store}>Tienda no disponible</option>}
          </select>
        </label>
        <div className="text-sm"><label htmlFor="offer-platform" className="block">Plataforma de esta oferta</label>
          <select id="offer-platform" aria-describedby="offer-platform-help" required value={platform} onChange={event => setPlatform(event.target.value)} className={fieldCls}>
            <option value="">Selecciona la plataforma confirmada</option>
            {platforms.map(item => <option key={item} value={item}>{item}</option>)}
            {platform && !platforms.includes(platform) && <option disabled value={platform}>{platform} (incompatible; revisar)</option>}
          </select>
          <div id="offer-platform-help">
          {platform && !game.platforms.includes(platform) && <span className="mt-2 block text-xs text-amber-300">Añade esta plataforma a la ficha del juego o selecciona una registrada.</span>}
          {selectedStore && storePlatforms(selectedStore) && !platforms.length && <span className="mt-2 block text-xs text-amber-300">Esta tienda no tiene plataformas compatibles con el juego.</span>}
          {selectedStore && !storePlatforms(selectedStore) && <span className="mt-2 block text-xs text-amber-300">La tienda no tiene plataformas configuradas. Confirma en la tienda la plataforma de esta oferta.</span>}
          </div>
        </div>
        <label className="block text-sm">Precio
          <input required type="number" min={0} step="any" value={price} onChange={event => setPrice(event.target.value)} className={fieldCls} />
        </label>
        <label className="block text-sm">Moneda ISO (CLP, USD…)
          <input required pattern="[A-Z]{3}" maxLength={3} value={currency} onChange={event => setCurrency(event.target.value.toUpperCase())} className={fieldCls} />
        </label>
        <label className="block text-sm sm:col-span-2">Enlace de compra
          <input type="url" maxLength={2000} value={url} onChange={event => setUrl(event.target.value)} className={fieldCls} />
        </label>
        {!game.platforms.length && <p className="text-sm text-amber-300 sm:col-span-2">Primero registra las plataformas disponibles en la sección Juegos.</p>}
        <button disabled={busy || !platforms.includes(platform)} className="rounded-lg bg-blue-600 px-4 py-3 text-sm font-bold text-white disabled:opacity-40">{busy ? 'Guardando…' : existing ? 'Guardar cambios de esta oferta' : 'Crear oferta para esta plataforma'}</button>
      </fieldset>
    </form>
  );
}
