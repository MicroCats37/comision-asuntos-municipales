/**
 * formatPublicId — Genera un ID público legible para las liquidaciones.
 *
 * Formato: {PREFIJO}-{AÑO}-{NÚMERO 6 dígitos}
 * Ej: EDIF-2026-000001
 *
 * - Prefijo según el tipo de liquidación
 * - Año de fecha_registro
 * - Número correlativo de la especialidad (padding 6 dígitos)
 */

const PREFIJOS: Record<string, string> = {
  edificacion: "EDIF",
  "habilitacion-urbana": "HU",
  "mecanica-suelos": "MS",
  "impacto-vial": "IV",
  taludes: "TALUD",
  "inspeccion-obra": "IO",
};

/** Obtiene el prefijo por tipo (fallback: primeras letras en mayúscula) */
export function getPrefijoTipo(tipo: string): string {
  if (PREFIJOS[tipo]) return PREFIJOS[tipo];
  return tipo
    .split("-")
    .map((p) => p.charAt(0).toUpperCase())
    .join("");
}

/** Extrae el año de una fecha ISO */
function getAnio(fechaRegistro?: string | null): string {
  if (!fechaRegistro) return "----";
  const d = new Date(fechaRegistro);
  if (Number.isNaN(d.getTime())) return "----";
  return String(d.getFullYear());
}

/**
 * Genera el ID público de una liquidación.
 * @param tipo "edificacion" | "taludes" | ...
 * @param fechaRegistro ISO date
 * @param numero correlativo de la especialidad (liquidacion_especifica.numero)
 */
export function formatPublicId(
  tipo: string,
  fechaRegistro?: string | null,
  numero?: number | null,
): string {
  const prefijo = getPrefijoTipo(tipo);
  const anio = getAnio(fechaRegistro);
  const num = numero != null ? String(numero).padStart(6, "0") : "------";
  return `${prefijo}-${anio}-${num}`;
}
