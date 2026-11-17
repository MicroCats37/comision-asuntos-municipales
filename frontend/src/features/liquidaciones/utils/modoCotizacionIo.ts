/**
 * Helpers del modo de cotización del motor IO (Inspección de Obra).
 *
 * - `MODO_COTIZACION_IO_POR_DEFECTO`: el modo vigente (cotización por valor
 *   completo). Todo lo que no declare modo se rehidrata como NORMAL.
 * - `resolverModoCotizacionPersistido`: una IO con registro de continuidad
 *   PERSISTIDO se rehidrata en modo CONTINUAR (su `sub_total` es la
 *   diferencia, no el valor completo).
 * - `hidratarModoCotizacionDesdeItem`: rehidratación desde el item.
 *
 * Espeja `utils/estrategiaCotizacion.ts` (patrón PO/Edificaciones).
 */
import {
  MODO_COTIZACION_IO_CONTINUAR,
  MODO_COTIZACION_IO_NORMAL,
  type ModoCotizacionIO,
  esModoCotizacionValido,
} from "../schemas/liquidacion-io-modo-cotizacion.schema";

/** Modo por defecto: el vigente y el que hereda todo lo que no declara modo. */
export const MODO_COTIZACION_IO_POR_DEFECTO: ModoCotizacionIO =
  MODO_COTIZACION_IO_NORMAL;

/**
 * Resuelve el modo de cotización de una IO a partir de su registro de
 * continuidad persistido.
 *
 * Con continuidad persistida → CONTINUAR: la liquidación cobra la diferencia y
 * su crédito está congelado; el panel "Normal" (valor completo) mentía.
 * Sin continuidad → NORMAL.
 */
export function resolverModoCotizacionPersistido(
  continuidad?: unknown | null,
): ModoCotizacionIO {
  return continuidad
    ? MODO_COTIZACION_IO_CONTINUAR
    : MODO_COTIZACION_IO_POR_DEFECTO;
}

export interface ModoCotizacionHidratacionInput {
  /** Bloque `liquidacion_tipo` de la liquidación persistida. */
  liquidacion_tipo?: { continuidad?: unknown } | null;
}

/**
 * Rehidratación del modo de cotización desde la liquidación persistida.
 *
 * No inventa datos: si el item no trae `liquidacion_tipo`, el modo es NORMAL.
 */
export function hidratarModoCotizacionDesdeItem(
  input: ModoCotizacionHidratacionInput,
): { modo_cotizacion: ModoCotizacionIO } {
  const modo = resolverModoCotizacionPersistido(input.liquidacion_tipo?.continuidad);
  return {
    modo_cotizacion: esModoCotizacionValido(modo)
      ? modo
      : MODO_COTIZACION_IO_POR_DEFECTO,
  };
}
