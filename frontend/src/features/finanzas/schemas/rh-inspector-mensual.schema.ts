/**
 * Zod schemas for RH Inspector Mensual — cotizar/crear endpoints.
 * Endpoint: POST /finanzas/recibos-inspectores/cotizar, POST /finanzas/recibos-inspectores/crear
 * Body In: { cip, periodo, items: [{exp_liqui, cantidad_visitas}] }
 * Body Out: { inspector_id, inspector_nombre, inspector_cip, periodo, items, totales, escala_descuento_id }
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

export const RHInspectorCotizarItemSchema = z.object({
  exp_liqui: z.string(),
  liquidacion_categoria_visitas_id: z.string(),
  inspecciones_programadas: z.number(),
  inspecciones_liquidadas: z.number(),
  costo_por_inspeccion: z.number(),
  monto_contribuido: z.number(),
  saldo_disponible: z.number(),
});

export const RHInspectorTotalesSchema = z.object({
  sub_total: z.number(),
  descuento: z.number(),
  honorarios: z.number(),
  tasa_descuento_aplicada: z.number(),
});

export const RHInspectorCotizarSchema = z.object({
  inspector_id: z.string(),
  inspector_nombre: z.string(),
  inspector_cip: z.string(),
  periodo: z.string(),
  items: z.array(RHInspectorCotizarItemSchema),
  totales: RHInspectorTotalesSchema,
  escala_descuento_id: z.string(),
});

export const RHInspectorCotizarResponseSchema = apiResponseSchema(
  RHInspectorCotizarSchema,
);

export const RHInspectorCotizarItemInSchema = z.object({
  exp_liqui: z.string(),
  cantidad_visitas: z.number(),
});

export const RHInspectorCotizarInSchema = z.object({
  cip: z.string(),
  periodo: z.string(),
  items: z.array(RHInspectorCotizarItemInSchema),
});

export type RHInspectorCotizar = z.infer<typeof RHInspectorCotizarSchema>;
export type RHInspectorCotizarItem = z.infer<
  typeof RHInspectorCotizarItemSchema
>;
export type RHInspectorCotizarItemIn = z.infer<
  typeof RHInspectorCotizarItemInSchema
>;
export type RHInspectorTotales = z.infer<typeof RHInspectorTotalesSchema>;
export type RHInspectorCotizarIn = z.infer<typeof RHInspectorCotizarInSchema>;
