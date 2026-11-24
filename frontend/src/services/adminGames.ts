import { jsonBody, request } from './http';
import { detailText, featuresFromAPI, requirementsFromAPI, type RequirementSet, type SystemRequirements } from './gameDetails';

export const requirementFields = [
  ['sistemaOperativo', 'Sistema operativo'], ['procesador', 'Procesador'],
  ['memoria', 'Memoria'], ['graficos', 'Gráficos'],
  ['almacenamiento', 'Almacenamiento'], ['notas', 'Notas'],
] as const;
export type RequirementDraft = Record<typeof requirementFields[number][0], string>;
export type EditableGame = {
  _id?: string; titulo: string; descripcion?: string | null; descripcionCorta?: string | null;
  desarrollador?: string | null; imagenPortada?: string | null; fechaLanzamiento?: string | null;
  generos?: string[]; plataformas?: string[]; activo?: boolean;
  caracteristicas?: string[]; requisitosSistema?: SystemRequirements | null;
};
export type GameDraft = {
  titulo: string; descripcion: string; descripcionCorta: string; desarrollador: string;
  imagenPortada: string; fechaLanzamiento: string; generos: string; plataformas: string;
  activo: boolean; caracteristicas: string; plataformaRequisitos: string;
  minimos: RequirementDraft; recomendados: RequirementDraft;
};
const text = (value: unknown) => typeof value === 'string' ? value : '';
const requirementDraft = (group?: RequirementSet): RequirementDraft => Object.fromEntries(
  requirementFields.map(([key]) => [key, text(group?.[key])]),
) as RequirementDraft;
export function gameDraft(game?: EditableGame): GameDraft {
  const requirements = requirementsFromAPI(game?.requisitosSistema);
  return {
    titulo: text(game?.titulo), descripcion: text(game?.descripcion), descripcionCorta: text(game?.descripcionCorta),
    desarrollador: text(game?.desarrollador), imagenPortada: text(game?.imagenPortada),
    fechaLanzamiento: text(game?.fechaLanzamiento).slice(0, 10),
    generos: game?.generos?.join(', ') || '', plataformas: game?.plataformas?.join(', ') || '',
    activo: game?.activo !== false, caracteristicas: featuresFromAPI(game?.caracteristicas).join('\n'),
    plataformaRequisitos: requirements?.plataforma || '',
    minimos: requirementDraft(requirements?.minimos), recomendados: requirementDraft(requirements?.recomendados),
  };
}
export function splitList(value: string, separator: string | RegExp = ','): string[] {
  const seen = new Set<string>();
  return value.split(separator).map(v => v.trim()).filter(v => {
    const key = v.toLocaleLowerCase('es');
    if (!v || seen.has(key)) return false;
    seen.add(key); return true;
  });
}
function requirementGroup(draft: RequirementDraft): RequirementSet | undefined {
  const entries = requirementFields.flatMap(([key]) => detailText(draft[key]) ? [[key, draft[key].trim()]] : []);
  return entries.length ? Object.fromEntries(entries) : undefined;
}
/** PUT conserva campos no editados: jamás reenvía ofertas, imágenes de fondo o metadatos. */
export function gamePayload(draft: GameDraft, original?: GameDraft): EditableGame {
  const payload: EditableGame = { titulo: draft.titulo.trim() };
  for (const key of ['descripcion', 'descripcionCorta', 'desarrollador', 'imagenPortada'] as const) {
    if (!original || draft[key] !== original[key]) payload[key] = draft[key].trim() || null;
  }
  if (!original || draft.fechaLanzamiento !== original.fechaLanzamiento) {
    payload.fechaLanzamiento = draft.fechaLanzamiento ? `${draft.fechaLanzamiento}T00:00:00Z` : null;
  }
  for (const key of ['generos', 'plataformas'] as const) {
    if (!original || draft[key] !== original[key]) payload[key] = splitList(draft[key]);
  }
  if (!original || draft.activo !== original.activo) payload.activo = draft.activo;
  if (!original || draft.caracteristicas !== original.caracteristicas) {
    payload.caracteristicas = splitList(draft.caracteristicas, /\r?\n/);
  }
  const requirementsChanged = !original || draft.plataformaRequisitos !== original.plataformaRequisitos ||
    JSON.stringify(draft.minimos) !== JSON.stringify(original.minimos) ||
    JSON.stringify(draft.recomendados) !== JSON.stringify(original.recomendados);
  if (requirementsChanged) {
    const minimos = requirementGroup(draft.minimos), recomendados = requirementGroup(draft.recomendados);
    if (minimos || recomendados) {
      if (!draft.plataformaRequisitos || !splitList(draft.plataformas).includes(draft.plataformaRequisitos)) {
        throw new Error('Selecciona una plataforma del juego para los requisitos.');
      }
      payload.requisitosSistema = { plataforma: draft.plataformaRequisitos, minimos, recomendados };
    } else {
      payload.requisitosSistema = null;
    }
  }
  // No se permite retirar la plataforma de requisitos existentes sin revisar ese bloque.
  if (draft.plataformaRequisitos && (requirementGroup(draft.minimos) || requirementGroup(draft.recomendados)) &&
      !splitList(draft.plataformas).includes(draft.plataformaRequisitos)) {
    throw new Error('La plataforma de los requisitos debe seguir incluida en las plataformas del juego.');
  }
  return payload;
}
export const loadAdminGame = (id: string, signal?: AbortSignal) =>
  request<EditableGame>(`/admin/juegos/${encodeURIComponent(id)}`, { signal });
export const saveAdminGame = (payload: EditableGame, id?: string) =>
  request<EditableGame>(id ? `/juegos/${encodeURIComponent(id)}` : '/juegos/', jsonBody(id ? 'PUT' : 'POST', payload));
