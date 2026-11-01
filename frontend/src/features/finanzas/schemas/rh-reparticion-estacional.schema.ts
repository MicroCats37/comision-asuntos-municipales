/**
 * Zod schemas for RH Reparticion Estacional (RH Trimestral).
 * Mirrors backend presentation schemas in:
 *   modules/finanzas/presentation/schemas/rh_reparticion_estacional_schemas.py
 *
 * Endpoints:
 *   GET  /liquidaciones/especialidades-revision
 *   GET  /liquidaciones/delegados/vigentes-por-especialidad?especialidad_revision_id=&fecha=
 *   POST /finanzas/reparticiones-estacionales/cotizar
 *   POST /finanzas/reparticiones-estacionales
 *   GET  /finanzas/reparticiones-estacionales
 *   PATCH /finanzas/reparticiones-estacionales/{id}
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
 * The delegate identity is nested; no duplicate flat identifier is exposed.
 */
export const RHReparticionEstacionalDelegadoSchema = z.object({
  delegado: DelegadoMinimalSchema,
  monto: num(),
});
export type RHReparticionEstacionalDelegado = z.infer<
  typeof RHReparticionEstacionalDelegadoSchema
>;

/**
 * Chapter share detail — mirrors RHReparticionEstacionalCapituloOut.
 * The chapter identity is nested; no duplicate flat identifier is exposed.
 */
export const RHReparticionEstacionalCapituloSchema = z.object({
  capitulo: CapituloMinimalSchema,
  monto: num(),
});
export type RHReparticionEstacionalCapitulo = z.infer<
  typeof RHReparticionEstacionalCapituloSchema
>;

// ── Input payloads (cotizar + crear + actualizar comparten el bloque general) ───

/**
 * Bloque general de entrada — mirrors backend RHReparticionEstacionalGeneralIn.
 *
 * The three operations (cotizar / crear / actualizar) compose the SAME block:
 * the backend defines it once and each operation schema extends it.
 */
export const RHReparticionEstacionalGeneralInSchema = z.object({
  especialidad_revision_id: z
    .string()
    .min(1, "Especialidad revision es requerida"),
  periodo: z.number().int().min(2000).max(2100),
  mes_desde: z.number().int().min(1).max(12),
  mes_hasta: z.number().int().min(1).max(12),
  delegado_ids: z.array(z.string()).min(1, "Al menos un delegado es requerido"),
});
export type RHReparticionEstacionalGeneralIn = z.infer<
  typeof RHReparticionEstacionalGeneralInSchema
>;

/** Input for POST /finanzas/reparticiones-estacionales/cotizar */
export const RHReparticionEstacionalCotizarInSchema =
  RHReparticionEstacionalGeneralInSchema;
export type RHReparticionEstacionalCotizarIn = z.infer<
  typeof RHReparticionEstacionalCotizarInSchema
>;

/** Input for POST /finanzas/reparticiones-estacionales */
export const RHReparticionEstacionalCrearInSchema =
  RHReparticionEstacionalGeneralInSchema;
export type RHReparticionEstacionalCrearIn = z.infer<
  typeof RHReparticionEstacionalCrearInSchema
>;

/** Input for PATCH /finanzas/reparticiones-estacionales/{id} */
export const RHReparticionEstacionalActualizarInSchema =
  RHReparticionEstacionalGeneralInSchema;
export type RHReparticionEstacionalActualizarIn = z.infer<
  typeof RHReparticionEstacionalActualizarInSchema
>;

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

// ── Persisted list output ──────────────────────────────────────────────────────

export const RHReparticionEstacionalIdentidadSchema = z.object({
  id: z.string(),
  created_at: z.string(),
});

export const RHReparticionEstacionalGeneralSchema = z.object({
  especialidad_revision: z.object({
    id: z.string(),
    nombre: z.string(),
  }),
  periodo: z.number().int(),
  mes_desde: z.number().int(),
  mes_hasta: z.number().int(),
});

export const RHReparticionEstacionalDistribucionSchema = z.object({
  total_fondo_comun: num(),
  numero_capitulos: z.number().int(),
  numero_delegados: z.number().int(),
  monto_por_participacion: num(),
  residual: num(),
  detalles_delegados: z.array(RHReparticionEstacionalDelegadoSchema),
  detalles_capitulos: z.array(RHReparticionEstacionalCapituloSchema),
});

/** Composed list item — mirrors RHReparticionEstacionalOut. */
export const RHReparticionEstacionalSchema = z.object({
  identidad: RHReparticionEstacionalIdentidadSchema,
  general: RHReparticionEstacionalGeneralSchema,
  distribucion: RHReparticionEstacionalDistribucionSchema,
});
export type RHReparticionEstacional = z.infer<
  typeof RHReparticionEstacionalSchema
>;

/**
 * Response envelope of a single persisted item.
 *
 * The PATCH endpoint returns the SAME composed item the list returns, so the
 * same schema validates both.
 */
export const RHReparticionEstacionalResponseSchema = apiResponseSchema(
  RHReparticionEstacionalSchema,
);

// ── Delete response ────────────────────────────────────────────────────────────

/**
 * Delete payload — mirrors RHReparticionEstacionalDeleteOut.
 *
 * The human-readable message lives only in the top level of the envelope
 * (contract/next-app-architecture-contract.md §11), so it is not repeated here.
 */
export const RHReparticionEstacionalDeleteSchema = z.object({
  id: z.string(),
});
export type RHReparticionEstacionalDelete = z.infer<
  typeof RHReparticionEstacionalDeleteSchema
>;
