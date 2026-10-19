/**
 * calculoGridCols — Tailwind grid responsive class string for the
 * "Tarifas aplicadas" / "Detalle técnico" mini-block.
 *
 * The grid grows columns with both N (number of items) and viewport so
 * the cells remain visually homogeneous regardless of how many fields
 * the motor exposes (PorcentajeObra can have 3 to 5 params; M2 / Visitas
 * have 3 each).
 *
 *  N | mobile | sm    | md    | lg     | xl
 * ---+--------+-------+-------+--------+---------
 *  1 | 1 col  | 1 col | 1 col | 1 col  | 1 col
 *  2 | 1 col  | 2 col | 2 col | 2 col  | 2 col
 *  3 | 1 col  | 2 col | 3 col | 3 col  | 3 col
 *  4 | 2 col  | 2 col | 2 col | 4 col  | 4 col
 *  5 | 2 col  | 2 col | 3 col | 4 col  | 5 col
 *  6+| 2 col | 2 col | 3 col | 4 col  | 5 col
 */
export function calculoGridCols(n: number): string {
  if (n <= 1) return "grid-cols-1";
  if (n === 2) return "grid-cols-1 sm:grid-cols-2";
  if (n === 3) return "grid-cols-1 sm:grid-cols-2 md:grid-cols-3";
  if (n === 4) return "grid-cols-2 md:grid-cols-2 lg:grid-cols-4";
  if (n === 5) return "grid-cols-2 md:grid-cols-3 xl:grid-cols-5";
  return "grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5";
}
