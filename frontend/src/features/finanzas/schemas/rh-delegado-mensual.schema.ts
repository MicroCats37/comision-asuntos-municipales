/**
 * Zod schemas for RH Delegado Mensual — cotizar/crear endpoints.
 * Endpoint: POST /finanzas/recibos-delegados/cotizar, POST /finanzas/recibos-delegados/crear
 * Body In: { cip, periodo, items: [{liquidacion_general_id, especialidad_revision_id}] }
 * Body Out: { delegado: {id, nombre_completo, cip}, periodo, items: [{exp_liqui, liquidacion_delegado_id, imp_bruto}], totales }
 *
 * Candidatas: GET /delegados/candidatas?cip={cip}
 *   → DelegadoCandidatasOut: { delegado, candidatas: CandidataOut[], total }
 *   → CandidataOut: { id, expediente, numero_revision, sub_total, total,
 *                     municipalidad_nombre, proyecto_denominacion, tipo_liquidacion,
 *                     especialidad_candidata: { id, nombre } }
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

// ── Nested types (mirror backend CandidataOut) ──────────────────────────────────

export const EspecialidadRevisionMinimalSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});

export const TipoLiquidacionMinimalSchema = z.object({
  codigo: z.string(),
  nombre: z.string(),
});

export const DelegadoMinimalSchema = z.object({
  id: z.string(),
  cip: z.string(),
  dni: z.string(),
  nombre_completo: z.string(),
});

// ── Shared schemas ──────────────────────────────────────────────────────────────

/** Minimal active comprobante data for RH Delegado item rows */
export const LiquidacionComprobanteMinimalSchema = z.object({
  tipo_comprobante: z.string().nullish(),
  serie: z.string().nullish(),
  numero: z.string().nullish(),
  fecha_emision: z.string().nullish(),
});

// ── Candidata item (from GET /delegados/candidatas) ────────────────────────────
export const CandidataDelegadoSchema = z.object({
  id: z.string(), // = liquidacion_general_id (UUID string)
  expediente: z.string().nullish(),
  numero_revision: z.coerce.number().int(),
  sub_total: z.number().nullish(),
  total: z.number().nullish(),
  municipalidad_nombre: z.string().nullish(),
  proyecto_denominacion: z.string().nullish(),
  tipo_liquidacion: TipoLiquidacionMinimalSchema.nullish(),
  especialidad_candidata: EspecialidadRevisionMinimalSchema,
  tipo_delegado: z.string(), // TITULAR or ALTERNO
  delegado_operacion_id: z.string(), // UUID string of DelegadoOperacion
  liquidacion_especifica_numero: z.coerce.number().int().nullish(), // numero from specific model
  comprobante_activo: LiquidacionComprobanteMinimalSchema.nullish(), // activo=True comprobante
});

export type CandidataDelegado = z.infer<typeof CandidataDelegadoSchema>;
export type DelegadoMinimal = z.infer<typeof DelegadoMinimalSchema>;

// ── DelegadoCandidatasOut (GET /delegados/candidatas response) ─────────────────
export const DelegadoCandidatasResponseSchema = apiResponseSchema(
  z.object({
    delegado: DelegadoMinimalSchema,
    candidatas: z.array(CandidataDelegadoSchema),
    total: z.number(),
  }),
);

// ── Input to cotizar + crear ──────────────────────────────────────────────────
// Periodo, dictamen_revision, fecha_presentacion y fecha_revision son por-item:
// se envían en cotizar y se persisten en LiquidacionDelegado durante crear.
export const RHDelegadoCotizarItemInSchema = z.object({
  liquidacion_general_id: z.string(), // UUID string — CandidataDelegado.id
  especialidad_revision_id: z.string(), // UUID string — CandidataDelegado.especialidad_candidata.id
  numero_rh: z.string().optional(), // Número de Orden/RH — se almacena en LiquidacionDelegado.numero_rh
  periodo: z.number().int().optional(), // Año — se almacena en LiquidacionDelegado.periodo
  mes: z.number().int().optional(), // Mes (1-12) — se almacena en LiquidacionDelegado.mes
  dictamen_revision: z.string().optional(), // se almacena en LiquidacionDelegado.dictamen_revision
  fecha_presentacion: z.string().optional(), // ISO date string — se almacena en LiquidacionDelegado.fecha_presentacion
  fecha_revision: z.string().optional(), // ISO date string — se almacena en LiquidacionDelegado.fecha_revision
  delegado_operacion_id: z.string().optional(), // UUID of DelegadoOperacion — falls back to top-level
});

export const RHDelegadoCotizarInSchema = z.object({
  cip: z.string(),
  periodo: z.string(), // "YYYY-MM" — periodo general del RH mensual
  delegado_operacion_id: z.string(), // UUID string of DelegadoOperacion — required for new RH flows
  items: z.array(RHDelegadoCotizarItemInSchema),
});

// ── Totales (from cotizar response) ──────────────────────────────────────────
// Note: Backend Decimal fields serialize as JSON strings. Use z.coerce.number()
// so string values like "123.45" parse to numbers while actual numbers are
// passed through unchanged. Invalid non-numeric strings still fail validation.
export const RHDelegadoTotalesSchema = z.object({
  sub_total: z.coerce.number(),
  renta_cip: z.coerce.number(), // 25% CIP
  aporte_codemu: z.coerce.number(), // 5%
  fondo_comun: z.coerce.number(), // 10%
  neto_honorario: z.coerce.number(),
});

// ── Cotizar output (mirrors RHDelegadoCotizarOut) ───────────────────────────────
// Note: Backend Decimal fields serialize as JSON strings. Use z.coerce.number()
// so string values like "123.45" parse to numbers while actual numbers are
// passed through unchanged. Invalid non-numeric strings still fail validation.

/** Variables de cálculo usadas en la cotización del RH Delegado */
export const RHDelegadoVariablesCalculoSchema = z.object({
  tasa_renta_cip: z.coerce.number(), // e.g. 0.25
  tasa_aporte_codemu: z.coerce.number(), // e.g. 0.05
  tasa_fondo_comun: z.coerce.number(), // e.g. 0.10
});

export const RHDelegadoCotizarItemSchema = z.object({
  exp_liqui: z.string(),
  // liquidacion_general_id and especialidad_revision_id are NOT returned by the backend
  // in the cotizar response — they are input-only fields.
  liquidacion_delegado_id: z.string().nullable().optional(), // backend may send null or omit
  delegado_operacion_id: z.string().nullish(), // UUID of DelegadoOperacion
  imp_bruto: z.coerce.number(),
  fecha_revision: z.string().nullish(),
  numero_revision: z.coerce.number().nullish(),
  total_liquidacion: z.coerce.number().nullish(),
  sub_total_liquidacion: z.coerce.number().nullish(),
  renta_cip: z.coerce.number().nullish(), // 25% CIP — per item
  aporte_codemu: z.coerce.number().nullish(), // 5% — per item
  fondo_comun: z.coerce.number().nullish(), // 10% — per item
  neto_honorario: z.coerce.number().nullish(), // per item
  numero_rh: z.string().nullish(),
  periodo: z.coerce.number().int().nullish(),
  mes: z.coerce.number().int().nullish(),
  dictamen_revision: z.string().nullish(),
  fecha_presentacion: z.string().nullish(),
  // Specific liquidation numero (e.g. Edificaciones numero)
  liquidacion_especifica_numero: z.coerce.number().int().nullish(),
  // Active comprobante for this liquidation
  comprobante_activo: LiquidacionComprobanteMinimalSchema.nullish(),
});

export const RHDelegadoDelegadoMinimalSchema = z.object({
  id: z.string(),
  nombre_completo: z.string(),
  cip: z.string(),
});

export const RHDelegadoCotizarSchema = z.object({
  delegado: RHDelegadoDelegadoMinimalSchema,
  periodo: z.string(),
  items: z.array(RHDelegadoCotizarItemSchema),
  totales: RHDelegadoTotalesSchema,
  variables_calculo: RHDelegadoVariablesCalculoSchema,
});

export const RHDelegadoCotizarResponseSchema = apiResponseSchema(
  RHDelegadoCotizarSchema,
);

// ── DelegadoOperacionVigente (from GET /delegados/operatividades-vigentes) ───────────
export const DelegadoOperacionVigenteSchema = z.object({
  id: z.string(), // UUID
  municipalidad_id: z.string(), // UUID
  municipalidad_nombre: z.string(),
  tipo_liquidacion_id: z.string().nullish(), // UUID or null (wildcard)
  tipo_liquidacion_codigo: z.string().nullish(),
  tipo_liquidacion_nombre: z.string().nullish(),
  especialidad_id: z.string(), // UUID
  especialidad_nombre: z.string(),
  tipo: z.string(), // TITULAR or ALTERNO
  periodo_inicio: z.string().nullish(), // ISO date
  periodo_fin: z.string().nullish(), // ISO date
});

export type DelegadoOperacionVigente = z.infer<typeof DelegadoOperacionVigenteSchema>;

export const DelegadoOperatividadesVigentesSchema = z.object({
  delegado_id: z.string(),
  cip: z.string(),
  nombre_completo: z.string(),
  operatividades: z.array(DelegadoOperacionVigenteSchema),
});

export type DelegadoOperatividadesVigentes = z.infer<
  typeof DelegadoOperatividadesVigentesSchema
>;

export const DelegadoOperatividadesVigentesResponseSchema = apiResponseSchema(
  DelegadoOperatividadesVigentesSchema,
);

// ── Types ──────────────────────────────────────────────────────────────────────
export type RHDelegadoCotizarIn = z.infer<typeof RHDelegadoCotizarInSchema>;
export type RHDelegadoCotizarItemIn = z.infer<
  typeof RHDelegadoCotizarItemInSchema
>;
export type RHDelegadoCotizar = z.infer<typeof RHDelegadoCotizarSchema>;
export type RHDelegadoTotales = z.infer<typeof RHDelegadoTotalesSchema>;
export type LiquidacionComprobanteMinimal = z.infer<
  typeof LiquidacionComprobanteMinimalSchema
>;
