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
});

export const RHDelegadoCotizarInSchema = z.object({
  cip: z.string(),
  periodo: z.string(), // "YYYY-MM" — periodo general del RH mensual
  items: z.array(RHDelegadoCotizarItemInSchema),
});

// ── Totales (from cotizar response) ──────────────────────────────────────────
export const RHDelegadoTotalesSchema = z.object({
  sub_total: z.number(),
  renta_cip: z.number(), // 25% CIP
  aporte_codemu: z.number(), // 5%
  fondo_comun: z.number(), // 10%
  neto_honorario: z.number(),
});

// ── Cotizar output (mirrors RHDelegadoCotizarOut) ───────────────────────────────
export const RHDelegadoCotizarItemSchema = z.object({
  exp_liqui: z.string(),
  // liquidacion_general_id and especialidad_revision_id are NOT returned by the backend
  // in the cotizar response — they are input-only fields.
  liquidacion_delegado_id: z.string().nullable().optional(), // backend may send null or omit
  imp_bruto: z.number(),
  fecha_revision: z.string().nullish(),
  numero_revision: z.number().nullish(),
  total_liquidacion: z.number().nullish(),
  sub_total_liquidacion: z.number().nullish(),
  renta_cip: z.number().nullish(), // 25% CIP — per item
  aporte_codemu: z.number().nullish(), // 5% — per item
  fondo_comun: z.number().nullish(), // 10% — per item
  neto_honorario: z.number().nullish(), // per item
  numero_rh: z.string().nullish(),
  periodo: z.number().int().nullish(),
  mes: z.number().int().nullish(),
  dictamen_revision: z.string().nullish(),
  fecha_presentacion: z.string().nullish(),
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
});

export const RHDelegadoCotizarResponseSchema = apiResponseSchema(
  RHDelegadoCotizarSchema,
);

// ── Types ──────────────────────────────────────────────────────────────────────
export type RHDelegadoCotizarIn = z.infer<typeof RHDelegadoCotizarInSchema>;
export type RHDelegadoCotizarItemIn = z.infer<
  typeof RHDelegadoCotizarItemInSchema
>;
export type RHDelegadoCotizar = z.infer<typeof RHDelegadoCotizarSchema>;
export type RHDelegadoTotales = z.infer<typeof RHDelegadoTotalesSchema>;
