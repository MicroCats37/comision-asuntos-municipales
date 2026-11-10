/**
 * Mirror Zod del endpoint anidado de detalle de asignaciones de delegado.
 *
 * Backend (contrato de lectura NUEVO, sin cambios en esta capa):
 *   GET /liquidaciones/{liquidacion_id}/delegados-asignaciones
 *   Response: ApiResponse[LiquidacionDelegadoDetalleResponseOut]
 *
 * Es un mirror de SOLO LECTURA: el frontend NO ofrece edición de la
 * asignación, así que este fichero NO declara ningún schema de request de
 * edición.
 *
 * Réplica 1:1 del wrapper
 * (backend/modules/liquidaciones/presentation/schemas/delegado/delegado_batch_schemas.py):
 *
 *   LiquidacionDelegadoDetalleResponseOut
 *   ├── liquidacion_id: uuid
 *   └── asignaciones: list[LiquidacionDelegadoDetalleOut]
 *       ├── (base) LiquidacionDelegadoOut        ← reutilizado, no duplicado
 *       ├── tipo: Optional[str]
 *       ├── numero_rh: Optional[str]
 *       ├── creado_por_rh: bool
 *       └── detalle_rh: list[DetalleHonorarioDelegadoOut]
 *           └── recibo_mensual: Optional[ReciboHonorarioDelegadoMensualOut]
 *
 * `ReciboHonorarioDelegadoMensual` NO tiene `imp_bruto` (solo `sub_total` y sus
 * derivados congelados) → el espejo no lo inventa. `DetalleHonorarioDelegado`
 * sí lo tiene.
 *
 * Sin `z.any()`: cada campo refleja el schema del backend (contrato
 * `api-wrapper-presenter-contract` §7).
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

// ── Bloques reutilizables (composición, no schema monolítico) ─────────────────

/** Especialidad de revisión — mirror de `EspecialidadRevisionOut`. */
const DetalleEspecialidadRevisionSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});

/** Tipo de liquidación mínimo — mirror de `TipoLiquidacionMinimalOut`. */
const DetalleTipoLiquidacionSchema = z.object({
  codigo: z.string(),
  nombre: z.string(),
});

/** Liquidación anidada — mirror de `LiquidacionDelegadoLiquidacionOut`. */
const DetalleLiquidacionSchema = z.object({
  id: z.string(),
  expediente: z.string().nullish(),
  numero_revision: z.coerce.number().int(),
  sub_total: z.coerce.number().nullish(),
  total: z.coerce.number().nullish(),
  municipalidad_nombre: z.string().nullish(),
  proyecto_denominacion: z.string().nullish(),
  tipo_liquidacion: DetalleTipoLiquidacionSchema.nullish(),
});

/** Delegado anidado — mirror de `LiquidacionDelegadoDelegadoOut`. */
const DetalleDelegadoSchema = z.object({
  id: z.string(),
  cip: z.string(),
  dni: z.string(),
  nombre_completo: z.string(),
});

// ── Response ──────────────────────────────────────────────────────────────────

/**
 * Cabecera del RH mensual enlazado a un detalle de honorario.
 * Mirror de `ReciboHonorarioDelegadoMensualOut`.
 */
export const ReciboHonorarioDelegadoMensualSchema = z.object({
  id: z.string(),
  numero: z.coerce.number().int().nullish(),
  periodo: z.coerce.number().int().nullish(),
  mes: z.coerce.number().int().nullish(),
  fecha_registro: z.string(),
  sub_total: z.coerce.number(),
  renta_cip: z.coerce.number(),
  aporte_codemu: z.coerce.number(),
  fondo_comun: z.coerce.number(),
  neto_honorario: z.coerce.number(),
});
export type ReciboHonorarioDelegadoMensual = z.infer<
  typeof ReciboHonorarioDelegadoMensualSchema
>;

/**
 * Detalle de honorario (RH) de una asignación, con su RH mensual enlazado.
 * Mirror de `DetalleHonorarioDelegadoOut`.
 *
 * `recibo_mensual` es null cuando el detalle está huérfano (sin RH mensual).
 */
export const DetalleHonorarioDelegadoSchema = z.object({
  id: z.string(),
  imp_bruto: z.coerce.number(),
  sub_total: z.coerce.number().nullish(),
  renta_cip: z.coerce.number().nullish(),
  aporte_codemu: z.coerce.number().nullish(),
  fondo_comun: z.coerce.number().nullish(),
  neto_honorario: z.coerce.number().nullish(),
  recibo_mensual: ReciboHonorarioDelegadoMensualSchema.nullish(),
});
export type DetalleHonorarioDelegado = z.infer<
  typeof DetalleHonorarioDelegadoSchema
>;

/**
 * Asignación (LiquidacionDelegado) enriquecida con su detalle RH.
 * Mirror de `LiquidacionDelegadoDetalleOut` (compone sobre `LiquidacionDelegadoOut`).
 */
export const LiquidacionDelegadoDetalleSchema = z.object({
  id: z.string(),
  liquidacion_id: z.string(),
  delegado_id: z.string(),
  especialidad_revision: DetalleEspecialidadRevisionSchema,
  liquidacion: DetalleLiquidacionSchema.nullish(),
  delegado: DetalleDelegadoSchema.nullish(),
  periodo: z.coerce.number().int().nullish(),
  mes: z.coerce.number().int().nullish(),
  dictamen_revision: z.string().nullish(),
  fecha_presentacion: z.string().nullish(),
  fecha_revision: z.string().nullish(),
  tipo: z.string().nullish(),
  numero_rh: z.string().nullish(),
  creado_por_rh: z.boolean(),
  detalle_rh: z.array(DetalleHonorarioDelegadoSchema),
});
export type LiquidacionDelegadoDetalle = z.infer<
  typeof LiquidacionDelegadoDetalleSchema
>;

/** Cuerpo de la respuesta — mirror de `LiquidacionDelegadoDetalleResponseOut`. */
export const LiquidacionDelegadoDetalleResponseSchema = z.object({
  liquidacion_id: z.string(),
  asignaciones: z.array(LiquidacionDelegadoDetalleSchema),
});
export type LiquidacionDelegadoDetalleResponse = z.infer<
  typeof LiquidacionDelegadoDetalleResponseSchema
>;

/** Envelope completo — mirror de `ApiResponse[LiquidacionDelegadoDetalleResponseOut]`. */
export const LiquidacionDelegadoDetalleApiResponseSchema = apiResponseSchema(
  LiquidacionDelegadoDetalleResponseSchema,
);
export type LiquidacionDelegadoDetalleApiResponse = z.infer<
  typeof LiquidacionDelegadoDetalleApiResponseSchema
>;

// ── Enum de `dictamen_revision` (presentación) ───────────────────────────────

/**
 * Valores admitidos por `dictamen_revision`.
 * Mirror de `DictamenRevision` (backend/modules/liquidaciones/domain/constants.py).
 *
 * El enum de Django se serializa como su string ("CONFORME"), no como objeto.
 *
 * Se usa para pintar la ETIQUETA legible del dictamen en la vista de solo
 * lectura: el frontend NO edita la asignación, así que no hay schema de
 * request de edición en este mirror.
 */
export const DICTAMEN_REVISION_VALUES = [
  "CONFORME",
  "NO_CONFORME",
  "PENDIENTE",
  "AP_OB",
] as const;

export type DictamenRevision = (typeof DICTAMEN_REVISION_VALUES)[number];
