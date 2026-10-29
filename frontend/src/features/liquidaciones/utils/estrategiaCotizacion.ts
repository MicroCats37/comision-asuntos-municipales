/**
 * Helpers de la estrategia de cotización PO (Edificaciones).
 *
 * - `resolverEstrategiaPersistida`: rehidratación. Las liquidaciones
 *   existentes (creadas antes de la estrategia persistida) se rehydratan como
 *   `NORMAL_SELECCIONADAS`, que es el backfill de la migración.
 * - `campoProhibidoPorEstrategia`: el dato que la estrategia activa no usa.
 * - `leerEstrategiaFormData`: lectura segura de los campos de estrategia
 *   desde un form data heterogéneo (Edificaciones las tiene; Taludes e
 *   Impacto Vial no).
 */

import type { EstrategiaCotizacionPOOut } from "../schemas/liquidacion-edificaciones.schema";
import {
  ESTRATEGIA_NORMAL,
  ESTRATEGIA_TOTAL,
  type EstrategiaCotizacionPO,
  esEstrategiaValida,
} from "../schemas/liquidacion-po-estrategia.schema";
import { toFiniteNumber } from "./toFiniteNumber";

/** Estrategia por defecto: la vigente y la que hereda todo lo legacy. */
export const ESTRATEGIA_POR_DEFECTO: EstrategiaCotizacionPO = ESTRATEGIA_NORMAL;

/** Campos del formulario que la estrategia activa puede reclamar. */
export type CampoEstrategia = "valor_declarado" | "total_explicito";

/**
 * Resuelve la estrategia persistida de una liquidación.
 *
 * `null`/`undefined`/un valor desconocido → `NORMAL_SELECCIONADAS`: las
 * liquidaciones legacy (y las que aún no tienen estrategia) se rehydratan con
 * el modo vigente.
 */
export function resolverEstrategiaPersistida(
  tipo: { estrategia_cotizacion?: string | null } | null | undefined,
): EstrategiaCotizacionPO {
  const persistida = tipo?.estrategia_cotizacion;
  return esEstrategiaValida(persistida) ? persistida : ESTRATEGIA_POR_DEFECTO;
}

/** `true` si la estrategia usa el valor declarado del proyecto. */
export function estrategiaUsaValorDeclarado(
  _estrategia: EstrategiaCotizacionPO,
): boolean {
  return true;
}

/** `true` si la estrategia usa el total final autoritativo con IGV. */
export function estrategiaUsaTotalExplicito(
  estrategia: EstrategiaCotizacionPO,
): boolean {
  return estrategia === ESTRATEGIA_TOTAL;
}

/**
 * Campo que debe limpiarse al cambiar de estrategia. TOTAL_EXPLICITO conserva
 * ambos datos; el resto no usa el total explícito.
 */
export function campoProhibidoPorEstrategia(
  estrategia: EstrategiaCotizacionPO,
): CampoEstrategia | null {
  return estrategiaUsaTotalExplicito(estrategia) ? null : "total_explicito";
}

export interface EstrategiaHidratarInput {
  /** Bloque `liquidacion_tipo` de la liquidación persistida. */
  liquidacion_tipo?: {
    estrategia_cotizacion?: string | null;
    valor_declarado?: number | string | null;
    total_explicito?: number | string | null;
  } | null;
}

/**
 * Rehidratación de los datos de estrategia desde la liquidación persistida.
 *
 * Sin pérdida de datos: se recupera la estrategia, el valor declarado y/o el
 * total explícito según la estrategia persistida. No se inventa un 0 para un
 * dato ausente.
 */
export function hidratarEstrategiaDesdeItem(input: EstrategiaHidratarInput): {
  estrategia_cotizacion: EstrategiaCotizacionPO;
  valor_declarado?: number;
  total_explicito?: number;
} {
  const tipo = input.liquidacion_tipo ?? null;
  const estrategia = resolverEstrategiaPersistida(tipo);

  const valorDeclarado = toFiniteNumber(tipo?.valor_declarado);
  const totalExplicito = toFiniteNumber(tipo?.total_explicito);

  if (estrategiaUsaTotalExplicito(estrategia)) {
    return {
      estrategia_cotizacion: estrategia,
      valor_declarado: valorDeclarado,
      total_explicito: totalExplicito,
    };
  }

  return {
    estrategia_cotizacion: estrategia,
    valor_declarado: valorDeclarado,
  };
}

export interface EstrategiaFormDataLectura {
  estrategia_cotizacion?: EstrategiaCotizacionPO;
  valor_declarado?: number;
  total_explicito?: number;
}

/**
 * Lee los campos de estrategia desde un form data heterogéneo.
 *
 * El formulario de Edificaciones tiene estrategia, valor declarado y total
 * explícito; los de Taludes e Impacto Vial no tienen ninguno de ellos. Esta
 * lectura evita castear el union `POFormData` y devuelve solo lo que existe.
 */
export function leerEstrategiaFormData(
  data: unknown,
): EstrategiaFormDataLectura {
  if (typeof data !== "object" || data === null) return {};
  const registro = data as Record<string, unknown>;

  const estrategia = registro.estrategia_cotizacion;
  const valorDeclarado = toFiniteNumber(registro.valor_declarado);
  const totalExplicito = toFiniteNumber(registro.total_explicito);

  return {
    ...(esEstrategiaValida(estrategia)
      ? { estrategia_cotizacion: estrategia }
      : {}),
    ...(valorDeclarado !== undefined
      ? { valor_declarado: valorDeclarado }
      : {}),
    ...(totalExplicito !== undefined
      ? { total_explicito: totalExplicito }
      : {}),
  };
}

/**
 * Lee el CONTEXTO de estrategia desde un `liquidacion_tipo` heterogéneo.
 *
 * Devuelve `null` cuando el bloque no trae estrategia: Taludes, Impacto Vial,
 * edge y las superficies de RH (que muestran el tipo de liquidación sin la
 * estrategia) no exponen esos campos. Es una lectura defensiva de
 * presentación: nunca lanza y nunca inventa datos.
 *
 * A diferencia de `leerEstrategiaFormData` (que lee un form data), aquí se
 * leen los campos ya proyectados por el backend: estrategia, snapshots
 * (H, total explícito, % tarifa) y la proyección de acumulación.
 */
export function leerContextoEstrategia(
  tipo: unknown,
): EstrategiaCotizacionPOOut | null {
  if (typeof tipo !== "object" || tipo === null) return null;
  const registro = tipo as Record<string, unknown>;

  const estrategia = registro.estrategia_cotizacion;
  if (typeof estrategia !== "string" || estrategia.trim() === "") return null;

  const acumulacion = registro.acumulacion;
  const contextoAcumulacion =
    typeof acumulacion === "object" && acumulacion !== null
      ? (acumulacion as Record<string, unknown>)
      : null;

  return {
    estrategia_cotizacion: estrategia,
    count_habilitadas: toFiniteNumber(registro.count_habilitadas) ?? null,
    total_explicito: toFiniteNumber(registro.total_explicito) ?? null,
    porcentaje_tarifa: toFiniteNumber(registro.porcentaje_tarifa) ?? null,
    tarifa_aplicada_id:
      typeof registro.tarifa_aplicada_id === "string"
        ? registro.tarifa_aplicada_id
        : null,
    acumulacion: contextoAcumulacion
      ? {
          porcentaje_acumulado:
            toFiniteNumber(contextoAcumulacion.porcentaje_acumulado) ?? null,
          subtotal_acumulado:
            toFiniteNumber(contextoAcumulacion.subtotal_acumulado) ?? 0,
        }
      : null,
  };
}
