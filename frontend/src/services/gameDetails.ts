/** Datos opcionales de la ficha. No deduce requisitos ni características de otros juegos. */
export type RequirementSet = { sistemaOperativo?: string; procesador?: string; memoria?: string; graficos?: string; almacenamiento?: string; notas?: string };
export type SystemRequirements = { plataforma?: string; minimos?: RequirementSet; recomendados?: RequirementSet };
export interface ExtraGameInfoAPI { descripcionCorta?: string | null; imagenFondo?: string | null; caracteristicas?: string[] | null; requisitosSistema?: SystemRequirements | null }
const fields = ['sistemaOperativo', 'procesador', 'memoria', 'graficos', 'almacenamiento', 'notas'] as const;
const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value);
export const detailText = (value: unknown): string | undefined => typeof value === 'string' && value.trim() ? value.trim() : undefined;
export function requirementsFromAPI(value: unknown): SystemRequirements | undefined {
  if (!object(value)) return;
  function group(raw: unknown): RequirementSet | undefined {
    if (!object(raw)) return;
    const entries = fields.flatMap(key => detailText(raw[key]) ? [[key, detailText(raw[key])]] : []);
    return entries.length ? Object.fromEntries(entries) : undefined;
  }
  const minimos = group(value.minimos), recomendados = group(value.recomendados);
  return minimos || recomendados ? { plataforma: detailText(value.plataforma), minimos, recomendados } : undefined;
}
export function featuresFromAPI(value: unknown): string[] {
  return Array.isArray(value) ? [...new Set(value.map(detailText).filter((item): item is string => !!item))] : [];
}
