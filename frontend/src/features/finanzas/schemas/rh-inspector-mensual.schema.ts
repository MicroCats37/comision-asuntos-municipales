/**
 * Zod schemas for RH Inspector Mensual — cotizar/crear endpoints.
 * Endpoint: POST /finanzas/recibos-inspectores/cotizar, POST /finanzas/recibos-inspectores/crear
 * Body In: { cip, periodo, items: [{exp_liqui, cantidad_visitas}] } or
 *          { cip, periodo, items: [{liquidacion_categoria_visitas_id, cantidad_visitas}] }
 * Body Out: { inspector: { id, nombre_completo, cip, dni }, periodo, items, totales, escala_descuento_id }
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

export const LiquidacionComprobanteMinimalSchema = z.object({
  tipo_comprobante: z.string().nullable().optional(),
  serie: z.string().nullable().optional(),
  numero: z.string().nullable().optional(),
  fecha_emision: z.string().nullable().optional(),
});

export const RHInspectorCotizarItemSchema = z.object({
  exp_liqui: z.string(),
  liquidacion_inspector_id: z.string(),
  liquidacion_categoria_visitas_id: z.string(),
  /**
   * Identificador estable de la fila persistida del RH (DetalleHonorarioInspector).
   * Es el token que el PATCH usa para CONSERVAR la fila en vez de re-agregarla.
   */
  detalle_id: z.string().nullable().optional(),
  nombre_propietario: z.string(),
  importe_bruto: z.coerce.number(),
  inspecciones_programadas: z.number(),
  inspecciones_liquidadas: z.number(),
  inspecciones_pagadas_hasta_mes_anterior: z.number(),
  costo_por_inspeccion: z.coerce.number(),
  monto_contribuido: z.coerce.number(),
  saldo_disponible: z.number(),
  saldo_restante: z.coerce.number().int(),
  /**
   * Valores financieros calculados por item (visibilidad de la cotización).
   * `tasa_descuento_aplicada` es una fracción decimal (ej. 0.20): el frontend
   * la convierte a porcentaje una sola vez al renderizarla.
   */
  sub_total: z.coerce.number(),
  descuento: z.coerce.number(),
  honorarios: z.coerce.number(),
  tasa_descuento_aplicada: z.coerce.number(),
  periodo: z.coerce.number().int().nullable().optional(),
  mes: z.coerce.number().int().nullable().optional(),
  // Número de la liquidación específica (e.g. LiquidacionInspeccionObra numero)
  liquidacion_especifica_numero: z.number().int().nullable().optional(),
  // Comprobante activo asociado a la liquidación
  comprobante_activo: LiquidacionComprobanteMinimalSchema.nullable().optional(),
});

export const RHInspectorTotalesSchema = z.object({
  sub_total: z.coerce.number(),
  descuento: z.coerce.number(),
  honorarios: z.coerce.number(),
  tasa_descuento_aplicada: z.coerce.number(),
});

export const RangoDescuentoSchema = z.object({
  monto_minimo: z.coerce.number(),
  monto_maximo: z.coerce.number().nullable(),
  porcentaje_descuento: z.coerce.number(), // fraction, e.g. 0.20
});

export const RHInspectorVariablesCalculoSchema = z.object({
  escala_id: z.string(),
  escala_nombre: z.string(),
  rango_aplicado: RangoDescuentoSchema,
});

export const InspectorMinimalSchema = z.object({
  id: z.string(),
  nombre_completo: z.string(),
  cip: z.string(),
  dni: z.string().nullish(),
});

export const RHInspectorCotizarSchema = z.object({
  inspector: InspectorMinimalSchema,
  periodo: z.number().int().nullish(),
  mes: z.number().int().nullish(),
  items: z.array(RHInspectorCotizarItemSchema),
  totales: RHInspectorTotalesSchema,
  escala_descuento_id: z.string(),
  variables_calculo: RHInspectorVariablesCalculoSchema,
  // Inspector operacion ID derived from selected items on create
  inspector_operacion_id: z.string().nullable().optional(),
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
  periodo: z.number().int().min(2000).max(2100),
  mes: z.number().int().min(1).max(12),
  items: z.array(RHInspectorCotizarItemInSchema),
});

// ── PATCH (sincronización del conjunto final) ─────────────────────────────────
// Endpoint: PATCH /finanzas/recibos-inspectores/{rh_id}
//
// El array `items` ES el conjunto final de detalles del recibo:
//   - item CON `detalle_id` → la fila persistida se CONSERVA (re-cotizada).
//   - item SIN `detalle_id` → la fila se AGREGA al recibo.
//   - filas persistidas ausentes del payload → se RETIRAN.
//
// Una fila persistida se identifica por `exp_liqui` (el backend resuelve la IO a
// partir del expediente); una fila nueva se identifica por
// `liquidacion_categoria_visitas_id` (candidata).
export const RHInspectorActualizarItemInSchema = z.object({
  exp_liqui: z.string().optional(),
  liquidacion_categoria_visitas_id: z.string().optional(),
  cantidad_visitas: z.number().int().min(1),
  periodo: z.number().int().optional(),
  mes: z.number().int().min(1).max(12).optional(),
  /** UUID del DetalleHonorarioInspector persistido — conserva la fila. */
  detalle_id: z.string().optional(),
  fecha_revision: z.string().optional(), // ISO date string
  fecha_presentacion: z.string().optional(), // ISO date string
});

export const RHInspectorActualizarInSchema = z.object({
  cip: z.string(),
  periodo: z.number().int().min(2000).max(2100),
  mes: z.number().int().min(1).max(12),
  items: z.array(RHInspectorActualizarItemInSchema),
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
export type RHInspectorActualizarIn = z.infer<
  typeof RHInspectorActualizarInSchema
>;
export type RHInspectorActualizarItemIn = z.infer<
  typeof RHInspectorActualizarItemInSchema
>;
export type LiquidacionComprobanteMinimal = z.infer<
  typeof LiquidacionComprobanteMinimalSchema
>;

// ── Inspector Candidatas (RH Mensual) ─────────────────────────────────────────

/**
 * DNI del inspector — `PerfilIngeniero.dni` es NULLABLE (ingenieros extranjeros),
 * igual que el `inspector_dni: Optional[str]` del backend. Se acepta null en el
 * borde y se normaliza a "" para no cambiar el tipo de salida que consumen los
 * hooks (que lo tipan como `string`).
 */
const inspectorDniSchema = z.string().nullish().transform((value) => value ?? "");

export const InspectorCandidataItemSchema = z.object({
  liquidacion_inspector_id: z.string(),
  liquidacion_categoria_visitas_id: z.string(),
  liquidacion_general_id: z.string(),
  expediente: z.string(),
  numero_revision: z.number(),
  fecha_registro: z.string(),
  inspector_nombre: z.string(),
  inspector_cip: z.string(),
  inspector_dni: inspectorDniSchema,
  especialidad_nombre: z.string(),
  nombre_propietario: z.string(),
  cantidad_visitas: z.number(),
  inspecciones_pagadas: z.number(),
  saldo_disponible: z.coerce.number().int(),
  costo_por_inspeccion: z.coerce.number(),
  total_liquidacion: z.coerce.number(),
  sub_total_liquidacion: z.coerce.number(),
  /**
   * Número de la liquidación específica (e.g. LiquidacionInspeccionObra.numero).
   * Es un dato DISTINTO de `numero_revision` (revisión) y del `numero` (RH de cabecera).
   */
  liquidacion_especifica_numero: z.coerce.number().int().nullish(),
  /** Comprobante activo (activo=True) de la liquidación. */
  comprobante_activo: LiquidacionComprobanteMinimalSchema.nullish(),
});

/** Legacy non-paginated shape — used by existing modals during transition */
export const InspectorCandidatosSchema = z.object({
  inspector_id: z.string(),
  inspector_nombre: z.string(),
  inspector_cip: z.string(),
  inspector_dni: inspectorDniSchema,
  periodo: z.string(),
  candidatos: z.array(InspectorCandidataItemSchema),
  total: z.number(),
});

/**
 * Paginated candidatas response from Module 1 backend.
 * Uses `items` (not `candidatos`) + pagination metadata.
 */
export const InspectorCandidatosPaginatedSchema = z.object({
  inspector_id: z.string(),
  inspector_nombre: z.string(),
  inspector_cip: z.string(),
  inspector_dni: inspectorDniSchema,
  periodo: z.string(),
  items: z.array(InspectorCandidataItemSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
  total_pages: z.number(),
});

export const InspectorCandidatosResponseSchema = apiResponseSchema(
  InspectorCandidatosSchema,
);

export const InspectorCandidatosPaginatedResponseSchema = apiResponseSchema(
  InspectorCandidatosPaginatedSchema,
);

export type InspectorCandidataItem = z.infer<
  typeof InspectorCandidataItemSchema
>;
export type InspectorCandidatos = z.infer<typeof InspectorCandidatosSchema>;
export type InspectorCandidatosPaginated = z.infer<
  typeof InspectorCandidatosPaginatedSchema
>;

// ── Operatividades RH de inspector ────────────────────────────────────────────

export const InspectorOperacionSchema = z.object({
  id: z.string(),
  nombre_completo: z.string(),
  cip: z.string(),
  especialidad: z.object({ id: z.string(), nombre: z.string() }).nullable(),
  tipo_liquidacion: z.string(),
  categoria: z.string().nullable(),
  numero_registro: z.string(),
  vigencia: z.string().nullable(),
  periodo_inicio: z.string().nullable(),
  periodo_fin: z.string().nullable(),
  es_vigente: z.boolean(),
  inspector_operacion_id: z.string(),
});

export const InspectorOperatividadesResponseSchema = apiResponseSchema(
  z.object({ inspectores: z.array(InspectorOperacionSchema) }),
);

export type InspectorOperacion = z.infer<typeof InspectorOperacionSchema>;
