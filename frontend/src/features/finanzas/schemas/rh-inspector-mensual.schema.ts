/**
 * Zod schemas for RH Inspector Mensual — cotizar/crear endpoints.
 * Endpoint: POST /finanzas/recibos-inspectores/cotizar, POST /finanzas/recibos-inspectores/crear
 * Body In: { cip, periodo, items: [{exp_liqui, cantidad_visitas}] } or
 *          { cip, periodo, items: [{liquidacion_categoria_visitas_id, cantidad_visitas}] }
 * Body Out: { inspector: { id, nombre_completo, cip, dni }, periodo, items, totales, escala_descuento_id }
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

export const RHInspectorCotizarItemSchema = z.object({
  exp_liqui: z.string(),
  liquidacion_inspector_id: z.string(),
  liquidacion_categoria_visitas_id: z.string(),
  nombre_propietario: z.string(),
  importe_bruto: z.number(),
  inspecciones_programadas: z.number(),
  inspecciones_liquidadas: z.number(),
  inspecciones_pagadas_hasta_mes_anterior: z.number(),
  costo_por_inspeccion: z.number(),
  monto_contribuido: z.number(),
  saldo_disponible: z.number(),
  saldo_restante: z.number(),
  periodo: z.number().nullable().optional(),
  mes: z.number().nullable().optional(),
});

export const RHInspectorTotalesSchema = z.object({
  sub_total: z.number(),
  descuento: z.number(),
  honorarios: z.number(),
  tasa_descuento_aplicada: z.number(),
});

export const InspectorMinimalSchema = z.object({
  id: z.string(),
  nombre_completo: z.string(),
  cip: z.string(),
  dni: z.string(),
});

export const RHInspectorCotizarSchema = z.object({
  inspector: InspectorMinimalSchema,
  periodo: z.string(),
  items: z.array(RHInspectorCotizarItemSchema),
  totales: RHInspectorTotalesSchema,
  escala_descuento_id: z.string(),
});

export const RHInspectorCotizarResponseSchema = apiResponseSchema(
  RHInspectorCotizarSchema,
);

export const RHInspectorCotizarItemInSchema = z.object({
  exp_liqui: z.string().optional(),
  /** Stable UUID — preferred over exp_liqui for candidate selection */
  liquidacion_categoria_visitas_id: z.string(),
  cantidad_visitas: z.number().int().min(1),
  periodo: z.number().int().optional(),
  mes: z.number().int().min(1).max(12).optional(),
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

// ── Inspector Candidatas (RH Mensual) ─────────────────────────────────────────

export const InspectorCandidataItemSchema = z.object({
  liquidacion_inspector_id: z.string(),
  liquidacion_categoria_visitas_id: z.string(),
  liquidacion_general_id: z.string(),
  expediente: z.string(),
  numero_revision: z.number(),
  fecha_registro: z.string(),
  inspector_nombre: z.string(),
  inspector_cip: z.string(),
  inspector_dni: z.string(),
  especialidad_nombre: z.string(),
  nombre_propietario: z.string(),
  cantidad_visitas: z.number(),
  inspecciones_pagadas: z.number(),
  saldo_disponible: z.number(),
  costo_por_inspeccion: z.number(),
  total_liquidacion: z.number(),
  sub_total_liquidacion: z.number(),
});

export const InspectorCandidatosSchema = z.object({
  inspector_id: z.string(),
  inspector_nombre: z.string(),
  inspector_cip: z.string(),
  inspector_dni: z.string(),
  periodo: z.string(),
  candidatos: z.array(InspectorCandidataItemSchema),
  total: z.number(),
});

export const InspectorCandidatosResponseSchema = apiResponseSchema(
  InspectorCandidatosSchema,
);

export type InspectorCandidataItem = z.infer<
  typeof InspectorCandidataItemSchema
>;
export type InspectorCandidatos = z.infer<typeof InspectorCandidatosSchema>;
