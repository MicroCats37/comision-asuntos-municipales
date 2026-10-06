/**
 * Zod schemas for RH Reparticion Estacional.
 * Mirrors backend presentation schemas in:
 *   modules/finanzas/presentation/schemas/rh_reparticion_estacional_schemas.py
 *
 * Endpoints:
 *   GET  /liquidaciones/especialidades-revision
 *   GET  /liquidaciones/delegados/vigentes-por-especialidad?especialidad_revision_id=&fecha=
 *   POST /finanzas/reparticiones-estacionales/cotizar
 *   POST /finanzas/reparticiones-estacionales
 *   GET  /finanzas/reparticiones-estacionales
 *   GET  /finanzas/reparticiones-estacionales/{id}
 *   DELETE /finanzas/reparticiones-estacionales/{id}
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

// Coerce helper: backend may serialize Decimal as string ("123.45") or number
const num = () => z.coerce.number();

// ── Minimal nested objects (mirrors backend DelegadoMinimalOut / CapituloMinimalOut) ──

/** Minimal delegate info — nested in detalle item, mirrors DelegadoMinimalOut */
export const DelegadoMinimalSchema = z.object({
  id: z.string(),
  cip: z.string(),
  dni: z.string(),
  nombre_completo: z.string(),
});
export type DelegadoMinimal = z.infer<typeof DelegadoMinimalSchema>;

/** Minimal chapter info — nested in detalle item, mirrors CapituloMinimalOut */
export const CapituloMinimalSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});
export type CapituloMinimal = z.infer<typeof CapituloMinimalSchema>;

// ── Detail item schemas ────────────────────────────────────────────────────────

/**
 * Delegate share detail — mirrors RHReparticionEstacionalDelegadoOut.
 * Nested `delegado` object is the primary shape; `delegado_id` is a backward-
 * compatibility alias kept for transition.
 */
export const RHReparticionEstacionalDelegadoSchema = z.object({
  delegado_id: z.string(),
  delegado: DelegadoMinimalSchema,
  monto: num(),
});
export type RHReparticionEstacionalDelegado = z.infer<
  typeof RHReparticionEstacionalDelegadoSchema
>;

/**
 * Chapter share detail — mirrors RHReparticionEstacionalCapituloOut.
 * Nested `capitulo` object is the primary shape; `capitulo_id` is a backward-
 * compatibility alias kept for transition.
 */
export const RHReparticionEstacionalCapituloSchema = z.object({
  capitulo_id: z.string(),
  capitulo: CapituloMinimalSchema,
  monto: num(),
});
export type RHReparticionEstacionalCapitulo = z.infer<
  typeof RHReparticionEstacionalCapituloSchema
>;

// ── Input payloads (cotizar + crear share the same shape) ─────────────────────

/** Input for POST /finanzas/reparticiones-estacionales/cotizar and /crear */
export const RHReparticionEstacionalCotizarInSchema = z.object({
  especialidad_revision_id: z
    .string()
    .min(1, "Especialidad revision es requerida"),
  periodo: z.number().int().min(2000).max(2100),
  mes_desde: z.number().int().min(1).max(12),
  mes_hasta: z.number().int().min(1).max(12),
  delegado_ids: z.array(z.string()).min(1, "Al menos un delegado es requerido"),
});
export type RHReparticionEstacionalCotizarIn = z.infer<
  typeof RHReparticionEstacionalCotizarInSchema
>;

// Alias for semantic clarity
export type RHReparticionEstacionalCrearIn = RHReparticionEstacionalCotizarIn;
export const RHReparticionEstacionalCrearInSchema =
  RHReparticionEstacionalCotizarInSchema;

// ── Cotizar output ─────────────────────────────────────────────────────────────

/** Cotizar response — mirrors RHReparticionEstacionalCotizarOut */
export const RHReparticionEstacionalCotizarSchema = z.object({
  especialidad_revision_id: z.string(),
  especialidad_revision_nombre: z.string(),
  periodo: z.number().int(),
  mes_desde: z.number().int(),
  mes_hasta: z.number().int(),
  total_fondo_comun: num(),
  numero_capitulos: z.number().int(),
  numero_delegados: z.number().int(),
  divisor_total: z.number().int(),
  monto_por_participacion: num(),
  residual: num(),
  detalles_delegados: z.array(RHReparticionEstacionalDelegadoSchema),
  detalles_capitulos: z.array(RHReparticionEstacionalCapituloSchema),
});
export type RHReparticionEstacionalCotizar = z.infer<
  typeof RHReparticionEstacionalCotizarSchema
>;

/** Response for cotizar + crear — both return RHReparticionEstacionalCotizarSchema */
export const RHReparticionEstacionalCotizarResponseSchema = apiResponseSchema(
  RHReparticionEstacionalCotizarSchema,
);

// ── List item ─────────────────────────────────────────────────────────────────

/** List item — mirrors RHReparticionEstacionalListItemOut */
export const RHReparticionEstacionalListItemSchema = z.object({
  id: z.string(),
  especialidad_revision_id: z.string(),
  especialidad_revision_nombre: z.string(),
  periodo: z.number().int(),
  total_fondo_comun: num(),
  numero_delegados: z.number().int(),
  numero_capitulos: z.number().int(),
  monto_por_participacion: num(),
  residual: num(),
  is_deleted: z.boolean(),
  created_at: z.string(),
});
export type RHReparticionEstacionalListItem = z.infer<
  typeof RHReparticionEstacionalListItemSchema
>;

// ── Detail ────────────────────────────────────────────────────────────────────

/** Full detail — mirrors RHReparticionEstacionalDetalleOut */
export const RHReparticionEstacionalDetalleSchema = z.object({
  id: z.string(),
  especialidad_revision_id: z.string(),
  especialidad_revision_nombre: z.string(),
  periodo: z.number().int(),
  mes_desde: z.number().int(),
  mes_hasta: z.number().int(),
  total_fondo_comun: num(),
  numero_capitulos: z.number().int(),
  numero_delegados: z.number().int(),
  monto_por_participacion: num(),
  residual: num(),
  is_deleted: z.boolean(),
  created_at: z.string(),
  detalles_delegados: z.array(RHReparticionEstacionalDelegadoSchema),
  detalles_capitulos: z.array(RHReparticionEstacionalCapituloSchema),
});
export type RHReparticionEstacionalDetalle = z.infer<
  typeof RHReparticionEstacionalDetalleSchema
>;

/** Response for GET /finanzas/reparticiones-estacionales/{id} — returns RHReparticionEstacionalDetalleSchema */
export const RHReparticionEstacionalDetalleResponseSchema = apiResponseSchema(
  RHReparticionEstacionalDetalleSchema,
);

// ── Delete response ────────────────────────────────────────────────────────────

/** Delete response — mirrors RHReparticionEstacionalDeleteOut */
export const RHReparticionEstacionalDeleteSchema = z.object({
  message: z.string(),
});
export type RHReparticionEstacionalDelete = z.infer<
  typeof RHReparticionEstacionalDeleteSchema
>;
