/**
 * Utilidades de formato de porcentajes de la cotización de RH mensual.
 *
 * El backend expone las tasas y los descuentos cotizados como FRACCIÓN
 * decimal (ej. `0.20` = 20%). Estas funciones son el ÚNICO lugar donde esa
 * fracción se convierte a porcentaje: hacerlo en un helper evita la doble
 * conversión (el bug `0.20%` en lugar de `20%`).
 */

/**
 * Convierte una tasa fraccionaria decimal a su valor porcentual.
 *
 * @param fraccion - Tasa como fracción decimal (ej. `0.20` → `20`).
 * @returns El porcentaje numérico, o `null` si la tasa no está disponible.
 */
export function toPercent(fraccion: number | null | undefined): number | null {
  if (fraccion == null || !Number.isFinite(fraccion)) return null;
  return fraccion * 100;
}

/**
 * Formatea una tasa fraccionaria decimal como porcentaje para mostrar.
 *
 * @param fraccion - Tasa como fracción decimal (ej. `0.20`).
 * @param decimales - Decimales del porcentaje (por defecto `0` → `"20%"`).
 * @returns El porcentaje formateado (ej. `"20%"`), o `null` si no hay tasa.
 */
export function formatPorcentaje(
  fraccion: number | null | undefined,
  decimales = 0,
): string | null {
  const porcentaje = toPercent(fraccion);
  if (porcentaje == null) return null;
  return `${porcentaje.toFixed(decimales)}%`;
}

/**
 * Añade el porcentaje cotizado a un rótulo de encabezado.
 *
 * @param etiqueta - Texto del encabezado (ej. `"Descuento"`).
 * @param fraccion - Tasa como fracción decimal (ej. `0.20`).
 * @param decimales - Decimales del porcentaje (por defecto `0`).
 * @returns `"Descuento (20%)"` o `"Descuento"` si no hay tasa disponible.
 */
export function etiquetaConPorcentaje(
  etiqueta: string,
  fraccion: number | null | undefined,
  decimales = 0,
): string {
  const porcentaje = formatPorcentaje(fraccion, decimales);
  return porcentaje == null ? etiqueta : `${etiqueta} (${porcentaje})`;
}
