/**
 * Helpers de PERÍODO (YYYY-MM) compartidos por los wizards RH mensuales
 * (Inspector y Delegado).
 *
 * Regla de negocio: el período por defecto de un RH mensual es el MES
 * CALENDARIO ANTERIOR al actual (con rollover de año: en enero el período
 * inicial es "YYYY-12" del año previo).
 *
 * El período NUNCA puede ser futuro: el selector `input[type=month]` acota
 * con `max` y la validación programática (`isFutureRhPeriod`) lo rechaza.
 */

export interface RhPeriodParts {
  /** Año (YYYY) como texto. */
  year: string;
  /** Mes (MM, con cero a la izquierda) como texto. */
  month: string;
  /** Período corto (YYYY-MM) como texto. */
  rhPeriod: string;
}

/**
 * Período del mes calendario ANTERIOR al actual.
 *
 * @param now Fecha de referencia (por defecto, hoy).
 */
export function getPreviousPeriodParts(now: Date = new Date()): RhPeriodParts {
  const year = now.getFullYear();
  // `getMonth()` es 0-based: el mes anterior es el índice - 1 → diciembre
  // del año previo cuando estamos en enero (índice 0).
  const monthIndex = now.getMonth();
  const prevYear = monthIndex === 0 ? year - 1 : year;
  const prevMonth = monthIndex === 0 ? 12 : monthIndex;
  const month = String(prevMonth).padStart(2, "0");

  return {
    year: String(prevYear),
    month,
    rhPeriod: `${prevYear}-${month}`,
  };
}

/**
 * Parsea un período "YYYY-MM" → `{ periodo, mes }` numéricos.
 * Devuelve `null` si el formato no es válido.
 */
export function parseRhPeriod(
  value: string | null | undefined,
): { periodo: number; mes: number } | null {
  if (!value) return null;
  const match = /^(\d{4})-(\d{2})$/.exec(value.trim());
  if (!match) return null;

  const periodo = Number(match[1]);
  const mes = Number(match[2]);
  if (!Number.isInteger(periodo) || !Number.isInteger(mes)) return null;
  if (mes < 1 || mes > 12) return null;

  return { periodo, mes };
}

/** ¿El período es posterior al mes actual? */
export function isFutureRhPeriod(
  periodo: number,
  mes: number,
  now: Date = new Date(),
): boolean {
  return (
    periodo > now.getFullYear() ||
    (periodo === now.getFullYear() && mes > now.getMonth() + 1)
  );
}
