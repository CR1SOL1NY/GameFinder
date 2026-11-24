import { useId, useState } from 'react';
import { type Game, dateLabel, money } from '../games';
import { Icon, PlatformLogo, platformBrand, type PlatformKey } from './common';

type Selection = { gameId: string; currency: string; platform: string | null };

function platformKey(name: string): PlatformKey | undefined {
  if (/^pc$/i.test(name)) return 'PC';
  if (/playstation|^ps[345]$/i.test(name)) return 'PlayStation';
  if (/xbox/i.test(name)) return 'Xbox';
  if (/switch/i.test(name)) return 'Switch';
}

function StoreBadge({ name }: { name: string }) {
  const colors: Record<string, string> = { steam: '#147ca5', eneba: '#7044e5', g2a: '#f26d2d', 'epic games store': '#35445e', 'humble store': '#db4057', 'green man gaming': '#339447' };
  return <span aria-hidden="true" className="grid size-8 shrink-0 place-items-center rounded-lg text-[10px] font-extrabold text-white" style={{ backgroundColor: colors[name.toLowerCase()] || '#35445e' }}>{name.replace(/[^\p{L}\p{N}]/gu, '').slice(0, 2).toUpperCase()}</span>;
}

export default function OfferComparison({ game }: { game: Game }) {
  const groupId = useId();
  const currencies = [...new Set(game.offers.map(offer => offer.currency))].sort();
  const platforms = [...new Set([
    ...game.platforms,
    ...game.offers.flatMap(offer => offer.platform ? [offer.platform] : []),
  ])];
  const defaultCurrency = currencies.includes('CLP') ? 'CLP' : currencies[0] || 'CLP';
  function defaultPlatform(currency: string) {
    const classified = game.offers.find(offer => offer.currency === currency && offer.platform);
    if (classified?.platform) return classified.platform;
    if (game.offers.some(offer => offer.currency === currency && !offer.platform)) return null;
    return platforms[0] ?? null;
  }
  const [selection, setSelection] = useState<Selection>(() => ({
    gameId: game.id,
    currency: defaultCurrency,
    platform: defaultPlatform(defaultCurrency),
  }));
  const sameGame = selection.gameId === game.id;
  const currency = sameGame && currencies.includes(selection.currency) ? selection.currency : defaultCurrency;
  const unknownOffers = game.offers.filter(offer => offer.currency === currency && !offer.platform);
  const platform = sameGame && (
    selection.platform === null ? unknownOffers.length > 0 : platforms.includes(selection.platform)
  ) ? selection.platform : defaultPlatform(currency);
  const offers = game.offers.filter(offer => offer.currency === currency && (
    platform === null ? !offer.platform : offer.platform === platform
  ));
  const comparable = /^[A-Z]{3}$/.test(currency);
  offers.sort((a, b) => comparable ? a.price - b.price : a.name.localeCompare(b.name));
  const best = platform !== null && comparable ? offers[0] : undefined;
  const tableTitle = platform === null ? 'Ofertas sin plataforma informada' : `Precios para ${platform}`;
  const countLabel = (count: number) => `${count} ${count === 1 ? 'oferta' : 'ofertas'} en ${currency}`;

  return (
    <section aria-label="Comparación de precios" className="space-y-3">
      <div className="rounded-xl border border-blue-500/25 bg-panel p-3">
        <fieldset>
          <legend className="mb-2 text-xs font-bold">Selecciona tu plataforma</legend>
          <div className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(${Math.min(platforms.length || 1, 4)}, minmax(0, 1fr))` }}>
            {platforms.map((value, index) => {
              const brand = platformKey(value);
              return (
                <label key={value} className="min-w-0 cursor-pointer">
                  <input type="radio" name={`${groupId}-platform`} value={`platform-${index}`} aria-label={value} checked={platform === value} onChange={() => setSelection({ gameId: game.id, currency, platform: value })} className="peer sr-only" />
                  <span className={`flex min-h-12 flex-col items-center justify-center gap-0.5 rounded-lg border px-1.5 py-1.5 text-center text-white transition hover:brightness-125 peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-blue-500 ${platform === value ? 'border-white ring-2 ring-slate-400/60 ring-offset-2 ring-offset-[#1E293B]' : 'border-white/15'}`} style={{ backgroundColor: brand ? platformBrand[brand].bg : '#16365C' }}>
                    {brand ? <PlatformLogo name={brand} className="size-5" /> : <Icon name="gamepad" className="size-5" />}
                    <b className="break-words text-[10px] font-semibold">{value}</b>
                  </span>
                </label>
              );
            })}
          </div>
          {!platforms.length && <p className="text-xs text-slate-400">Todavía no se informaron plataformas para este juego.</p>}
          {unknownOffers.length > 0 && <div className="mt-3 border-t border-blue-500/20 pt-3">
            <label className="flex cursor-pointer items-center gap-2 text-[11px] text-slate-300"><input type="radio" name={`${groupId}-platform`} value="unclassified" checked={platform === null} onChange={() => setSelection({ gameId: game.id, currency, platform: null })} className="size-4 shrink-0 accent-blue-500" />Sin plataforma informada ({unknownOffers.length})</label>
            <p className="mt-2 text-[10px] leading-5 text-amber-300">{platform === null ? 'Estas ofertas todavía no tienen una plataforma asociada. Confírmala en la tienda antes de comprar.' : `${unknownOffers.length} ${unknownOffers.length === 1 ? 'oferta sin plataforma informada queda fuera' : 'ofertas sin plataforma informada quedan fuera'} de los precios para ${platform}.`}</p>
          </div>}
        </fieldset>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
          <p className="text-[10px] text-slate-400">Seleccionada: <b className="font-semibold text-slate-300">{platform || 'Sin plataforma informada'}</b></p>
          {currencies.length > 1 ? <label className="flex items-center gap-2 text-[10px] text-slate-400">Moneda<select value={currency} onChange={event => setSelection({ gameId: game.id, currency: event.target.value, platform })} className="rounded-md border border-blue-500/25 bg-field px-2 py-1.5 text-xs text-fg">{(currencies.length ? currencies : ['CLP']).map(value => <option key={value}>{value}</option>)}</select></label> : <span className="text-[10px] text-slate-400">{currency}</span>}
        </div>
      </div>
      <section className="overflow-hidden rounded-xl border border-blue-500/25 bg-panel">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-blue-500/20 px-3.5 py-3" aria-live="polite" aria-atomic="true">
          <h2 className="flex items-center gap-2 text-xs font-bold"><Icon name={platform === 'PC' ? 'monitor' : 'gamepad'} className="size-4 text-slate-300" />{tableTitle}</h2>
          <span className="text-[10px] text-slate-400">{countLabel(offers.length)}</span>
        </div>
        {!comparable && <p className="p-4 text-xs text-amber-300">Estas ofertas no informan una moneda válida; no se calcula un precio mínimo.</p>}
        {offers.length > 0 ? <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <caption className="sr-only">{tableTitle} de {game.title}, en {currency}. Cada moneda se compara por separado.</caption>
            <thead className="sr-only"><tr><th scope="col">Tienda / plataforma</th><th scope="col">Precio</th><th scope="col">Compra</th></tr></thead>
            <tbody>{offers.map((offer, index) => <tr key={offer.id || `${offer.storeId}-${offer.platform}-${index}`} className={`border-t border-blue-500/15 first:border-t-0 ${best && offer.price === best.price ? 'bg-blue-500/5' : ''}`}>
              <td className="px-3 py-2"><div className="flex items-start gap-2"><StoreBadge name={offer.name} /><div className="min-w-0"><div className="flex flex-wrap items-center gap-1"><b className="break-words text-[11px]">{offer.name}</b>{best && offer.price === best.price && <span className="inline-block rounded bg-emerald-500/20 px-1.5 py-0.5 text-[9px] text-emerald-300">Más barato</span>}</div><span className="mt-1 block text-[10px] text-slate-400">{offer.platform || 'Plataforma no informada'}</span>{offer.updatedAt && <span className="mt-1 block text-[9px] text-slate-400">Actualizado: {dateLabel(offer.updatedAt)}</span>}</div></div></td>
              <td className="whitespace-nowrap px-1 py-2 text-right text-xs font-bold">{money(offer.price, offer.currency)}<span className="mt-0.5 block text-[9px] font-normal text-slate-400">{offer.currency}</span></td>
              <td className="pl-2 pr-3 py-2 text-right">{offer.url ? <a href={offer.url} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-10 items-center justify-center gap-1 whitespace-nowrap rounded-md bg-blue-600 px-2.5 py-2 text-[10px] font-bold text-white hover:bg-blue-500">Ver oferta <span aria-hidden="true">↗</span><span className="sr-only"> en {offer.name} (nueva pestaña)</span></a> : <span className="text-[10px] text-slate-400">Sin enlace</span>}</td>
            </tr>)}</tbody>
          </table>
        </div> : <div role="status" className="px-5 py-8 text-center"><Icon name="search" className="mx-auto size-7 text-blue-400" /><h3 className="mt-3 text-sm font-bold">{platform === null ? 'Sin ofertas para esta moneda' : `Sin ofertas para ${platform}`}</h3><p className="mt-2 text-xs leading-5 text-slate-400">No hay precios registrados para esta selección. Prueba otra plataforma o moneda.</p></div>}
        <p className="border-t border-blue-500/20 px-3.5 py-3 text-[10px] leading-5 text-slate-400">Confirma la edición, región y disponibilidad en la tienda antes de comprar.</p>
      </section>
    </section>
  );
}
