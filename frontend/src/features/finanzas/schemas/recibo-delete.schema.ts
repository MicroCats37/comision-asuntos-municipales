/**
 * Zod schemas for RH Inspector and Delegado Mensual delete responses.
 * Mirrors backend:
 *   modules/finanzas/presentation/schemas/finanzas_schemas.py
 *     → RHInspectorDeleteOut: { id: UUID, message: str }
 *     → RHDelegadoDeleteOut:  { id: UUID, message: str }
 *
 * Endpoints:
 *   DELETE /finanzas/recibos-inspectores/{id}/eliminar
 *   DELETE /finanzas/recibos-delegados/{id}/eliminar
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

/** Delete response — mirrors RHInspectorDeleteOut */
export const RHInspectorDeleteSchema = z.object({
  id: z.string().uuid(),
  message: z.string(),
});
export type RHInspectorDelete = z.infer<typeof RHInspectorDeleteSchema>;

export const RHInspectorDeleteResponseSchema = apiResponseSchema(
  RHInspectorDeleteSchema,
);

/** Delete response — mirrors RHDelegadoDeleteOut */
export const RHDelegadoDeleteSchema = z.object({
  id: z.string().uuid(),
  message: z.string(),
});
export type RHDelegadoDelete = z.infer<typeof RHDelegadoDeleteSchema>;

export const RHDelegadoDeleteResponseSchema = apiResponseSchema(
  RHDelegadoDeleteSchema,
);
