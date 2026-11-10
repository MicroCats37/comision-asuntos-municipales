/**
 * Mirror Zod del contrato batch de delegados de liquidación.
 *
 * Backend (contrato REUTILIZADO, sin cambios):
 *   PATCH /liquidaciones/{liquidacion_id}/delegados
 *   Request:  { create: [{ delegado_id }], update: [{ delegated_id, ... }], delete: [{ delegado_id }] }
 *   Response: { created: [...], updated: [...], deleted: [delegado_id] }
 *
 * La acción "Quitar delegado" usa SOLO la rama `delete` y con UN único item:
 * un PATCH por fila. Un batch multi-fila es atómico, así que un solo rechazo
 * (409) abortaría las demás filas y el operador no podría saber cuáles sí
 * procedían.
 *
 * Sin `z.any()`: cada campo refleja el schema del backend
 * (backend/.../delegado_batch_schemas.py).
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

// ── Request ───────────────────────────────────────────────────────────────────

/** Item de entrada de la rama `delete` — { delegado_id }. */
export const LiquidacionDelegadoDeleteInSchema = z.object({
  delegado_id: z.string(),
});
export type LiquidacionDelegadoDeleteIn = z.infer<
  typeof LiquidacionDelegadoDeleteInSchema
>;

/** Payload de "Quitar delegado" — exactamente un item en `delete`. */
export const QuitarDelegadoBatchRequestSchema = z.object({
  delete: z.array(LiquidacionDelegadoDeleteInSchema).min(1),
});
export type QuitarDelegadoBatchRequest = z.infer<
  typeof QuitarDelegadoBatchRequestSchema
>;

// ── Response ──────────────────────────────────────────────────────────────────

/** Especialidad del item del batch — mirror de EspecialidadRevisionOut. */
const BatchItemEspecialidadRevisionSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});

/** Liquidación anidada — mirror de LiquidacionDelegadoLiquidacionOut. */
const BatchItemLiquidacionSchema = z.object({
  id: z.string(),
  expediente: z.string().nullish(),
  numero_revision: z.coerce.number().int(),
  sub_total: z.coerce.number().nullish(),
  total: z.coerce.number().nullish(),
  municipalidad_nombre: z.string().nullish(),
  proyecto_denominacion: z.string().nullish(),
  tipo_liquidacion: z
    .object({ codigo: z.string(), nombre: z.string() })
    .nullish(),
});

/** Delegado anidado — mirror de LiquidacionDelegadoDelegadoOut. */
const BatchItemDelegadoSchema = z.object({
  id: z.string(),
  cip: z.string(),
  dni: z.string(),
  nombre_completo: z.string(),
});

/** Item de salida — mirror de LiquidacionDelegadoOut. */
export const LiquidacionDelegadoBatchItemOutSchema = z.object({
  id: z.string(),
  liquidacion_id: z.string(),
  delegado_id: z.string(),
  especialidad_revision: BatchItemEspecialidadRevisionSchema,
  liquidacion: BatchItemLiquidacionSchema.nullish(),
  delegado: BatchItemDelegadoSchema.nullish(),
  periodo: z.coerce.number().int().nullish(),
  mes: z.coerce.number().int().nullish(),
  dictamen_revision: z.string().nullish(),
  fecha_presentacion: z.string().nullish(),
  fecha_revision: z.string().nullish(),
});
export type LiquidacionDelegadoBatchItemOut = z.infer<
  typeof LiquidacionDelegadoBatchItemOutSchema
>;

/** Cuerpo de la respuesta — mirror de LiquidacionDelegadoBatchOut. */
export const LiquidacionDelegadoBatchOutSchema = z.object({
  created: z.array(LiquidacionDelegadoBatchItemOutSchema),
  updated: z.array(LiquidacionDelegadoBatchItemOutSchema),
  deleted: z.array(z.string()),
});
export type LiquidacionDelegadoBatchOut = z.infer<
  typeof LiquidacionDelegadoBatchOutSchema
>;

/** Envelope completo de la respuesta — mirror de ApiResponse[BatchOut]. */
export const LiquidacionDelegadoBatchResponseSchema = apiResponseSchema(
  LiquidacionDelegadoBatchOutSchema,
);
export type LiquidacionDelegadoBatchResponse = z.infer<
  typeof LiquidacionDelegadoBatchResponseSchema
>;
