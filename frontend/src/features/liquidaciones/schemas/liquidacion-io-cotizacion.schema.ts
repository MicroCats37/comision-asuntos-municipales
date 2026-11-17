/**
 * Espejo EXACTO del contrato de cotización del motor IO (Inspección de Obra).
 *
 * Backend (fuente de verdad):
 *   `backend/modules/liquidaciones/presentation/schemas/liquidacion_especifico/
 *    liquidacion_inspeccion_obra_schemas.py` → union discriminada SOLO de IO.
 *
 * Hay exactamente DOS modos:
 *   - `NORMAL`    → la cotización vigente (sin continuidad). El discriminador
 *     es OPCIONAL en el backend (el payload vigente queda byte-compatible);
 *     aquí se materializa siempre para que el payload sea explícito.
 *   - `CONTINUAR` → la liquidación cobra la DIFERENCIA entre el valor completo
 *     del trabajo y el crédito de la liquidación previa (A). El discriminador y
 *     el bloque `continuidad` son OBLIGATORIOS.
 *
 * El bloque `continuidad` de la COTIZACIÓN lleva SOLO el dato DECLARADO por el
 * cliente (`total_pagado_previa`, monto BRUTO pagado en la IO previa, IGV
 * incluido). NO lleva `liquidacion_previa_id`: la ruta de cotización no
 * desreferencia la liquidación previa (DD-8). El servidor valida la declaración
 * y deriva el par (crédito neto, crédito bruto) con el IGV efectivo de la ruta.
 *
 * Cada variante declara `strict` (equivalente a `extra="forbid"` en el backend):
 * un payload mixto (continuidad en NORMAL), incompleto (CONTINUAR sin
 * `total_pagado_previa`) o con campos desconocidos se rechaza.
 *
 * Los bloques compartidos de Visitas (`datos`, `tarifa`) NO se tocan
 * (SCHEMA_DRY_INTENTION): se COMPONEN igual que en el backend, donde
 * `BaseSchema` no prohíbe claves extra en los bloques anidados.
 *
 * Taludes, Impacto Vial, HU, MS y legacy NO usan este contrato.
 */
import { z } from "zod";
import {
  MODO_COTIZACION_IO_CONTINUAR,
  MODO_COTIZACION_IO_NORMAL,
  type ModoCotizacionIO,
} from "./liquidacion-io-modo-cotizacion.schema";

export { MODO_COTIZACION_IO_CONTINUAR, MODO_COTIZACION_IO_NORMAL };
export type { ModoCotizacionIO };

/** Máximo compatible con `DecimalField(max_digits=12, decimal_places=2)`. */
export const TOTAL_PAGADO_PREVIA_MAXIMO = 9999999999.99;

export const MENSAJE_TOTAL_PAGADO_PREVIA_POSITIVO =
  "El total pagado en la liquidación previa debe ser mayor a 0";
export const MENSAJE_TOTAL_PAGADO_PREVIA_MAXIMO =
  "El total pagado en la liquidación previa excede el máximo permitido";
export const MENSAJE_TOTAL_PAGADO_PREVIA_NUMERO =
  "El total pagado en la liquidación previa debe ser un número válido";

// ── Request: bloques compartidos (composición, no duplicación) ──────────────

/**
 * `datos` de la cotización (espejo de `LiquidacionPorCategoriaVisitasDatosIn`
 * y `CotizarEdicionVisitasDatosIn`: misma forma en ambas rutas).
 */
export const cotizarVisitasDatosSchema = z.object({
  cantidad_visitas: z.coerce
    .number()
    .int("La cantidad de visitas debe ser un número entero")
    .positive("La cantidad de visitas debe ser positiva"),
  categoria: z.string().optional(),
});

/** `tarifa` de la cotización (espejo de `...TarifaIn` de ambas rutas). */
export const cotizarVisitasTarifaSchema = z.object({
  tarifa_visitas_id: z.string().min(1, "La tarifa es requerida"),
});

/**
 * Bloque `continuidad` DECLARADO por el cliente (espejo de
 * `LiquidacionInspeccionObraCotizarContinuidadIn`).
 *
 * `strict` ≡ `extra="forbid"`: un bloque con claves desconocidas se rechaza.
 */
export const cotizacionIoContinuidadInSchema = z.strictObject({
  total_pagado_previa: z.coerce
    .number({
      error: (issue) =>
        issue.input === undefined || issue.input === null || issue.input === ""
          ? MENSAJE_TOTAL_PAGADO_PREVIA_NUMERO
          : MENSAJE_TOTAL_PAGADO_PREVIA_NUMERO,
    })
    .positive(MENSAJE_TOTAL_PAGADO_PREVIA_POSITIVO)
    .max(TOTAL_PAGADO_PREVIA_MAXIMO, MENSAJE_TOTAL_PAGADO_PREVIA_MAXIMO),
});

// ── Request: union discriminada de la cotización de ALTA ─────────────────────

/** NORMAL — cotización de alta (el discriminador es opcional en el backend). */
export const cotizarVisitasNormalSchema = z.strictObject({
  modo_cotizacion: z.literal(MODO_COTIZACION_IO_NORMAL),
  datos: cotizarVisitasDatosSchema,
  tarifa: cotizarVisitasTarifaSchema,
});

/** CONTINUAR — cotización de alta con el bruto declarado. */
export const cotizarVisitasContinuarSchema = z.strictObject({
  modo_cotizacion: z.literal(MODO_COTIZACION_IO_CONTINUAR),
  datos: cotizarVisitasDatosSchema,
  tarifa: cotizarVisitasTarifaSchema,
  continuidad: cotizacionIoContinuidadInSchema,
});

/**
 * Union discriminada de la cotización de ALTA — espejo exacto de
 * `LiquidacionInspeccionObraCotizarEspecificaIn` del backend.
 */
export const cotizarVisitasSchema = z.discriminatedUnion("modo_cotizacion", [
  cotizarVisitasNormalSchema,
  cotizarVisitasContinuarSchema,
]);

export type CotizarVisitasPayload = z.infer<typeof cotizarVisitasSchema>;

// ── Request: union discriminada de la cotización de EDICIÓN ──────────────────
//
// Misma union que el alta, pero con el wrapper `liquidacion_tipo` (que NO
// cambia) y con `tarifa` OBLIGATORIA (igual que hoy).

/** NORMAL — cotización de edición (el discriminador es opcional). */
export const cotizarVisitasEdicionNormalSchema = z.strictObject({
  modo_cotizacion: z.literal(MODO_COTIZACION_IO_NORMAL),
  datos: cotizarVisitasDatosSchema,
  tarifa: cotizarVisitasTarifaSchema,
});

/** CONTINUAR — cotización de edición con el bruto declarado. */
export const cotizarVisitasEdicionContinuarSchema = z.strictObject({
  modo_cotizacion: z.literal(MODO_COTIZACION_IO_CONTINUAR),
  datos: cotizarVisitasDatosSchema,
  tarifa: cotizarVisitasTarifaSchema,
  continuidad: cotizacionIoContinuidadInSchema,
});

/**
 * Union discriminada de la cotización de EDICIÓN — espejo exacto de
 * `LiquidacionInspeccionObraCotizarEdicionTipoIn` del backend.
 */
export const cotizarVisitasEdicionSchema = z.discriminatedUnion(
  "modo_cotizacion",
  [cotizarVisitasEdicionNormalSchema, cotizarVisitasEdicionContinuarSchema],
);

export type CotizarVisitasEdicionPayload = z.infer<
  typeof cotizarVisitasEdicionSchema
>;

// ── Response: espejo del bloque autoritativo de continuidad ──────────────────

/**
 * Bloque `continuidad` de la RESPUESTA (espejo de
 * `LiquidacionInspeccionObraCotizarContinuidadOut`).
 *
 * Son las cifras AUTORITATIVAS del servidor: el cliente las RENDERIZA, no las
 * recalcula (DD-7). `total_pagado_previa` es el eco del bruto declarado;
 * `credito_neto` / `credito_bruto` son el par DERIVADO por el servidor con el
 * IGV efectivo de la ruta; `diferencia_*` es lo que la liquidación nueva cobra.
 */
export const cotizacionVisitasContinuidadOutSchema = z.looseObject({
  total_pagado_previa: z.coerce.number(),
  valor_completo_neto: z.coerce.number(),
  valor_completo_bruto: z.coerce.number(),
  credito_neto: z.coerce.number(),
  credito_bruto: z.coerce.number(),
  diferencia_neto: z.coerce.number(),
  diferencia_bruto: z.coerce.number(),
  igv_porcentaje: z.coerce.number(),
});

export type CotizacionVisitasContinuidadOut = z.infer<
  typeof cotizacionVisitasContinuidadOutSchema
>;

/**
 * Bloque `datos` de la respuesta (bloque COMPARTIDO del backend: no se
 * re-define aquí, se lee). Es permisivo a propósito: el detalle de
 * inspectores y registros de pago no lo consume el cliente y no debe romper
 * el parseo.
 */
export const cotizacionVisitasDatosOutSchema = z
  .looseObject({
    entrada: z.looseObject({
      datos: z.looseObject({ cantidad_visitas: z.coerce.number().catch(0) }),
      tarifa: z.looseObject({
        tarifa_visitas_id: z.string().catch(""),
      }),
    }),
    tarifa: z.looseObject({
      id: z.string().catch(""),
      costo_por_visita: z.coerce.number().catch(0),
    }),
    variables_financieras: z.looseObject({
      igv: z.looseObject({ valor: z.coerce.number().catch(0) }).catch({
        valor: 0,
      }),
      uit: z.looseObject({ valor: z.coerce.number().catch(0) }).catch({
        valor: 0,
      }),
    }),
  })
  .catch({
    entrada: {
      datos: { cantidad_visitas: 0 },
      tarifa: { tarifa_visitas_id: "" },
    },
    tarifa: { id: "", costo_por_visita: 0 },
    variables_financieras: { igv: { valor: 0 }, uit: { valor: 0 } },
  });

/** Bloque `calculo` de la respuesta (el VALOR COMPLETO de B). */
export const cotizacionVisitasCalculoOutSchema = z
  .object({
    monto_bruto: z.coerce.number().catch(0),
    subtotal: z.coerce.number().catch(0),
    total: z.coerce.number().catch(0),
  })
  .catch({ monto_bruto: 0, subtotal: 0, total: 0 });

/**
 * Salida de la cotización de IO — espejo de
 * `LiquidacionInspeccionObraCotizarOutput`.
 *
 * La respuesta se ENSANCHA: `datos` y `calculo` no cambian, el eco
 * `modo_cotizacion` siempre viaja y el bloque `continuidad` es opcional
 * (`null` en NORMAL).
 *
 * Tipar la respuesta con este esquema es lo que impide que Zod elimine las
 * claves nuevas (riesgo R9 del Explorer).
 */
export const cotizacionVisitasOutputSchema = z.object({
  datos: cotizacionVisitasDatosOutSchema,
  calculo: cotizacionVisitasCalculoOutSchema,
  modo_cotizacion: z
    .enum([MODO_COTIZACION_IO_NORMAL, MODO_COTIZACION_IO_CONTINUAR])
    .optional(),
  continuidad: cotizacionVisitasContinuidadOutSchema.nullish().catch(null),
});

export type CotizacionVisitasOutput = z.infer<
  typeof cotizacionVisitasOutputSchema
>;

/**
 * Parsea la respuesta de la cotización con el espejo Zod.
 *
 * Es el punto donde el backend y el frontend quedan atados: si el servidor
 * añade una clave al bloque `continuidad`, el espejo la conserva (Zod no la
 * elimina) y el panel puede renderizarla.
 */
export function parseCotizacionVisitasOutput(
  payload: unknown,
): CotizacionVisitasOutput {
  return cotizacionVisitasOutputSchema.parse(payload);
}

// ── Normalización y parsing ─────────────────────────────────────────────────

/**
 * Materializa el discriminador cuando el payload no lo trae.
 *
 * Espejo del backend: el discriminador es opcional únicamente para `NORMAL`,
 * de modo que el payload vigente (modo normal) permanece byte-compatible.
 */
export function normalizarPayloadCotizacionVisitas<
  T extends Record<string, unknown>,
>(payload: T): T & { modo_cotizacion: ModoCotizacionIO } {
  const discriminador = payload.modo_cotizacion;
  if (
    discriminador === MODO_COTIZACION_IO_NORMAL ||
    discriminador === MODO_COTIZACION_IO_CONTINUAR
  ) {
    return payload as T & { modo_cotizacion: ModoCotizacionIO };
  }
  return {
    ...payload,
    modo_cotizacion: MODO_COTIZACION_IO_NORMAL,
  };
}

/** Parsea un payload de cotización aplicando la normalización previa. */
export function parsePayloadCotizacionVisitas(payload: unknown) {
  return cotizarVisitasSchema.parse(
    normalizarPayloadCotizacionVisitas(
      (payload ?? {}) as Record<string, unknown>,
    ),
  );
}

/** Igual que `parsePayloadCotizacionVisitas`, pero para la ruta de edición. */
export function parsePayloadCotizacionVisitasEdicion(payload: unknown) {
  return cotizarVisitasEdicionSchema.parse(
    normalizarPayloadCotizacionVisitas(
      (payload ?? {}) as Record<string, unknown>,
    ),
  );
}

// ── Builders del payload discriminado ───────────────────────────────────────

export interface CotizacionVisitasPayloadInput {
  /** Modo de cotización vigente (NORMAL | CONTINUAR). */
  modo: ModoCotizacionIO;
  /** Cantidad de visitas de B. */
  cantidad_visitas: number;
  /** Tarifa vigente (o histórica en la ruta de edición). */
  tarifa_visitas_id: string;
  /**
   * BRUTO declarado pagado en la IO previa (IGV incluido).
   *
   * Solo viaja en CONTINUAR: es el dato que el servidor valida y convierte en
   * el par (crédito neto, crédito bruto). En NORMAL no existe el bloque.
   */
  total_pagado_previa?: number;
}

/**
 * Construye el cuerpo discriminado de `POST /inspeccion-obra/cotizar`.
 *
 * El wrapper NO cambia (`liquidacion_especifica`): lo que cambia es el
 * contenido de la variante, que materializa el discriminador y —en
 * CONTINUAR— el bloque `continuidad` con el bruto DECLARADO.
 */
export function construirCotizacionVisitasPayload(
  input: CotizacionVisitasPayloadInput,
): { liquidacion_especifica: CotizarVisitasPayload } {
  return {
    liquidacion_especifica: construirVarianteCotizacionVisitas(input),
  };
}

/**
 * Construye el cuerpo discriminado de `POST /inspeccion-obra/{id}/cotizar-edicion`.
 *
 * El wrapper es OTRO (`liquidacion_tipo`) y NO cambia (riesgo R13).
 */
export function construirCotizacionVisitasEdicionPayload(
  input: CotizacionVisitasPayloadInput,
): { liquidacion_tipo: CotizarVisitasEdicionPayload } {
  return {
    liquidacion_tipo: construirVarianteCotizacionVisitas(input),
  };
}

/**
 * Construye la VARIANTE (el interior del wrapper) compartida por ambas rutas.
 *
 * El backend NO desreferencia la liquidación previa en la ruta de cotización
 * (DD-8): por eso el bloque `continuidad` solo lleva el bruto declarado.
 */
function construirVarianteCotizacionVisitas(
  input: CotizacionVisitasPayloadInput,
): CotizarVisitasPayload {
  const datos = { cantidad_visitas: input.cantidad_visitas };
  const tarifa = { tarifa_visitas_id: input.tarifa_visitas_id };

  // Barrera final: un modo desconocido NUNCA se envía — degrada a NORMAL (el
  // modo vigente y el único que el backend acepta con el discriminador
  // ausente).
  const modo: ModoCotizacionIO =
    input.modo === MODO_COTIZACION_IO_CONTINUAR
      ? MODO_COTIZACION_IO_CONTINUAR
      : MODO_COTIZACION_IO_NORMAL;

  if (modo === MODO_COTIZACION_IO_CONTINUAR) {
    const totalPagadoPrevia = input.total_pagado_previa;
    // Sin bruto declarado NO se construye la variante CONTINUAR: el backend la
    // rechaza con 422 (`total_pagado_previa` es obligatorio). El cliente no
    // inventa el dato: espera a que el usuario lo declare.
    if (totalPagadoPrevia === undefined || !(totalPagadoPrevia > 0)) {
      return {
        modo_cotizacion: MODO_COTIZACION_IO_NORMAL,
        datos,
        tarifa,
      };
    }
    return {
      modo_cotizacion: MODO_COTIZACION_IO_CONTINUAR,
      datos,
      tarifa,
      continuidad: { total_pagado_previa: totalPagadoPrevia },
    };
  }

  return {
    modo_cotizacion: MODO_COTIZACION_IO_NORMAL,
    datos,
    tarifa,
  };
}
