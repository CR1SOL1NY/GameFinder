import type { Game } from '../games';
import type { RequirementSet } from '../services/gameDetails';

const requirements: [keyof RequirementSet, string][] = [['sistemaOperativo', 'SO'], ['procesador', 'Procesador'], ['memoria', 'Memoria'], ['graficos', 'Gráficos'], ['almacenamiento', 'Almacenamiento'], ['notas', 'Notas']];

function RequirementsColumn({ title, data }: { title: string; data?: RequirementSet }) {
  return <div><h4 className="text-xs font-bold">{title}</h4>{data ? <dl className="mt-4 space-y-2 text-xs leading-5 text-slate-400">{requirements.map(([key, label]) => data[key] ? <div key={key} className="break-words"><dt className="inline text-slate-300">{label}: </dt><dd className="inline">{data[key]}</dd></div> : null)}</dl> : <p className="mt-4 text-xs leading-5 text-slate-400">La fuente de datos todavía no informa estos requisitos.</p>}</div>;
}

export default function GameInformation({ game }: { game: Game }) {
  const system = game.systemRequirements;
  return <div className="space-y-7 py-6">
    <section aria-labelledby="game-description-title"><h2 id="game-description-title" className="text-lg font-bold">Descripción del juego</h2><p className="mt-4 whitespace-pre-wrap break-words text-sm leading-7 text-slate-300">{game.description}</p></section>
    {!!game.features?.length && <section aria-labelledby="game-features-title"><h3 id="game-features-title" className="text-sm font-bold">Lo que encontrarás en el juego</h3><ul className="mt-4 grid gap-x-8 gap-y-3 sm:grid-cols-2">{game.features.map(feature => <li key={feature} className="flex gap-2 text-xs leading-5 text-slate-300"><span aria-hidden="true" className="text-blue-400">•</span><span className="break-words">{feature}</span></li>)}</ul></section>}
    <section aria-labelledby="game-requirements-title" className="rounded-xl border border-blue-500/25 bg-panel p-5"><h3 id="game-requirements-title" className="text-sm font-bold">Requisitos del sistema{system?.plataforma ? ` (${system.plataforma})` : ''}</h3><div className="mt-5 grid gap-7 sm:grid-cols-2"><RequirementsColumn title="Mínimos" data={system?.minimos} /><RequirementsColumn title="Recomendados" data={system?.recomendados} /></div></section>
  </div>;
}
