/**
 * Discriminador de MODO DE COTIZACIÓN del motor IO (Inspección de Obra).
 *
 * Espeja el patrón de PO/Edificaciones (`estrategia_cotizacion`) para el motor
 * de Visitas: el modo vive en el FORM (RHF) y el SmartField de tarifas es el
 * dueño de la composición — un solo formulario, un solo SmartField, una sola
 * llamada de cotización.
 *
 *  · `NORMAL`    → la liquidación se cotiza por su VALOR COMPLETO (comportamiento
 *    vigente). El bloque de continuidad no se toca: no viaja en el payload.
 *  · `CONTINUAR` → la liquidación cobra la DIFERENCIA entre el valor completo
 *    del trabajo y el crédito de la liquidación previa (A). El panel de
 *    continuidad (referencia histórica, crédito y diferencia) es el panel
 *    activo del SmartField.
 *
 * NO es el mismo concepto que `continuidad.modo` (`activar` | `mantener` |
 * `desactivar`): aquel es el discriminador de la OPERACIÓN de continuidad del
 * PATCH de IO y viaja DENTRO del bloque `liquidacion_tipo.continuidad`.
 *
 * Este discriminador SÍ viaja al backend: es el discriminador de la UNION de
 * modos de la cotización de IO (`modo_cotizacion`), materializado por los
 * builders de `liquidacion-io-cotizacion.schema.ts`. En CONTINUAR viaja
 * además el bloque `continuidad` con el bruto DECLARADO
 * (`total_pagado_previa`); el servidor devuelve las cifras autoritativas
 * (valor completo, crédito y diferencia) y el cliente no hace aritmética
 * monetaria.
 */
import { z } from "zod";

// ── Constantes canónicas ────────────────────────────────────────────────────

export const MODO_COTIZACION_IO_NORMAL = "NORMAL";
export const MODO_COTIZACION_IO_CONTINUAR = "CONTINUAR";

/** Los DOS modos de cotización del motor IO, en el orden de la UI. */
export const MODOS_COTIZACION_IO = [
  MODO_COTIZACION_IO_NORMAL,
  MODO_COTIZACION_IO_CONTINUAR,
] as const;

export type ModoCotizacionIO = (typeof MODOS_COTIZACION_IO)[number];

/** Etiquetas legibles del selector de modo. */
export const MODO_COTIZACION_IO_LABELS: Record<ModoCotizacionIO, string> = {
  [MODO_COTIZACION_IO_NORMAL]: "Normal",
  [MODO_COTIZACION_IO_CONTINUAR]: "Continuar",
};

/** Descripción corta del alcance de cada modo (ayuda contextual). */
export const MODO_COTIZACION_IO_DESCRIPCIONES: Record<
  ModoCotizacionIO,
  string
> = {
  [MODO_COTIZACION_IO_NORMAL]:
    "La liquidación se cotiza por el valor completo del trabajo. La continuidad de visitas no se modifica.",
  [MODO_COTIZACION_IO_CONTINUAR]:
    "La liquidación cobra la diferencia entre el valor completo del trabajo y el crédito de la liquidación previa.",
};

export const modoCotizacionIOSchema = z.enum(MODOS_COTIZACION_IO);

/** `true` si el valor es uno de los DOS modos canónicos. */
export function esModoCotizacionValido(
  valor: unknown,
): valor is ModoCotizacionIO {
  return (
    typeof valor === "string" &&
    (MODOS_COTIZACION_IO as readonly string[]).includes(valor)
  );
}
