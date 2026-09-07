/**
 * Zod schemas for Recibos de Honorarios — mirrors backend ReciboHonorarioDelegadoOut.
 * Endpoint: GET /finanzas/recibos-honorarios, POST /finanzas/recibos-honorarios
 */
import { z } from "zod";
import { TipoLiquidacionMinimalSchema } from "./tipo-liquidacion-minimal.schema";

const uuid = () => z.string();
const num = () => z.coerce.number();

export { TipoLiquidacionMinimalSchema as tipoLiquidacionMinimalSchema } from "./tipo-liquidacion-minimal.schema";

export const liquidacionGeneralMinimalSchema = z.object({
  id: uuid(),
  expediente: z.string().nullish(),
  numero_revision: z.coerce.number().int(),
  sub_total: num(),
  total: num(),
  fecha_registro: z.string(),
  tipo_liquidacion: TipoLiquidacionMinimalSchema.nullish(),
  municipalidad_nombre: z.string().nullish(),
  proyecto_denominacion: z.string().nullish(),
});

export const delegadoMinimalSchema = z.object({
  id: uuid(),
  cip: z.string(),
  dni: z.string().nullish(),
  nombre_completo: z.string(),
});

export const especialidadMinimalSchema = z.object({
  id: uuid(),
  nombre: z.string(),
});

export const reciboHonorarioCalculoSchema = z.object({
  sub_total: num(),
  imp_bruto: num(),
  renta_cip: num(),
  aporte_codemu: num(),
  fondo_comun: num(),
  neto_honorario: num(),
  honorario: num(),
});

export const liquidacionEspecificaMinimalSchema = z.object({
  id: uuid(),
  numero: z.coerce.number(),
});

/** ReciboHonorarioDelegadoOut — matches backend schema exactly */
export const reciboHonorarioDelegadoSchema = z.object({
  id: uuid(),
  liquidacion_delegado_id: uuid(),
  liquidacion_general: liquidacionGeneralMinimalSchema,
  liquidacion_especifica: liquidacionEspecificaMinimalSchema,
  delegado: delegadoMinimalSchema,
  especialidad: especialidadMinimalSchema,
  calculo: reciboHonorarioCalculoSchema,
  created_at: z.string(),
});

export type ReciboHonorarioDelegado = z.infer<
  typeof reciboHonorarioDelegadoSchema
>;

// ── Inspector ─────────────────────────────────────────────────────────────────

export const inspectorMinimalSchema = z.object({
  id: uuid(),
  cip: z.string(),
  dni: z.string(),
  nombre_completo: z.string(),
});

export const reciboHonorarioInspectorCalculoSchema = z.object({
  inspecciones_programadas: z.coerce.number().int(),
  costo_por_inspeccion: num(),
  inspecciones_mes: z.coerce.number().int(),
  monto_bruto: num(),
  inspecciones_pagadas: z.coerce.number().int(),
  saldo_inspecciones: z.coerce.number().int(),
  sub_total: num(),
  tasa_descuento_aplicada: num(),
  descuento: num(),
  honorarios: num(),
});

/** ReciboHonorarioInspectorOut — matches backend schema exactly */
export const reciboHonorarioInspectorSchema = z.object({
  id: uuid(),
  liquidacion_inspector_id: uuid(),
  liquidacion_general: liquidacionGeneralMinimalSchema,
  liquidacion_especifica: liquidacionEspecificaMinimalSchema,
  inspector: inspectorMinimalSchema,
  especialidad: especialidadMinimalSchema,
  calculo: reciboHonorarioInspectorCalculoSchema,
  created_at: z.string(),
});

export type ReciboHonorarioInspector = z.infer<
  typeof reciboHonorarioInspectorSchema
>;

// ── RH Delegado Mensual — Listado ─────────────────────────────────────────────

/** Minimal comprobante schema — shared between RH Delegado and RH Inspector */
const comprobanteMinimalSchema = z.object({
  tipo_comprobante: z.string().nullish(),
  serie: z.string().nullish(),
  numero: z.string().nullish(),
  fecha_emision: z.string().nullish(),
});

export const rhDelegadoMensualDetalleSchema = z.object({
  liquidacion_delegado_id: uuid(),
  expediente: z.string(),
  fecha_revision: z.string().nullish(),
  numero_revision: z.number().int().nullish(),
  total_liquidacion: num().nullish(),
  sub_total_liquidacion: num().nullish(),
  numero_rh: z.string().nullish(),
  imp_bruto: num(),
  renta_cip: num().nullish(),
  aporte_codemu: num().nullish(),
  fondo_comun: num().nullish(),
  neto_honorario: num().nullish(),
  periodo: z.number().int().nullish(),
  mes: z.number().int().nullish(),
  dictamen_revision: z.string().nullish(),
  fecha_presentacion: z.string().nullish(),
  delegado_operacion_id: z.string().nullish(),
  liquidacion_especifica_numero: z.number().int().nullish(),
  comprobante_activo: comprobanteMinimalSchema.nullish(),
});

export const rhDelegadoMensualTotalesSchema = z.object({
  sub_total: num(),
  renta_cip: num(),
  aporte_codemu: num(),
  fondo_comun: num(),
  neto_honorario: num(),
});

/** Variables de cálculo para el RH Delegado Mensual — tasas vigentes */
export const rhDelegadoVariablesCalculoSchema = z.object({
  tasa_renta_cip: z.coerce.number(),
  tasa_aporte_codemu: z.coerce.number(),
  tasa_fondo_comun: z.coerce.number(),
});

/** Contexto completo de la operatividad del delegado — municipalidad, tipo liq., especialidad, rol */
export const delegadoOperacionContextSchema = z.object({
  id: uuid(),
  municipalidad_id: uuid(),
  municipalidad_nombre: z.string(),
  tipo_liquidacion_id: uuid().nullish(),
  tipo_liquidacion_codigo: z.string().nullish(),
  tipo_liquidacion_nombre: z.string().nullish(),
  especialidad_id: uuid(),
  especialidad_nombre: z.string(),
  tipo: z.string(),
});

/** RHDelegadoMensualListItemOut — matches backend schema exactly */
export const rhDelegadoMensualListItemSchema = z.object({
  id: uuid(),
  periodo: z.number().int().nullish(),
  mes: z.number().int().nullish(),
  fecha_registro: z.string(),
  delegado: delegadoMinimalSchema,
  totales: rhDelegadoMensualTotalesSchema,
  detalles: z.array(rhDelegadoMensualDetalleSchema),
  variables_calculo: rhDelegadoVariablesCalculoSchema,
  delegado_operacion_id: z.string().nullish(),
  delegado_operacion_context: delegadoOperacionContextSchema.nullish(),
});

export type ReciboHonorarioDelegadoMensual = z.infer<
  typeof rhDelegadoMensualListItemSchema
>;

// ── RH Inspector Mensual — Listado ─────────────────────────────────────────────

export const rhInspectorMensualDetalleSchema = z.object({
  expediente: z.string(),
  nombre_propietario: z.string(),
  distrito: z.string().nullish(),
  importe_bruto: num(),
  inspecciones_programadas: z.coerce.number().int(),
  inspecciones_liquidadas: z.coerce.number().int(),
  inspecciones_pagadas_hasta_mes_anterior: z.coerce.number().int(),
  costo_por_inspeccion: num(),
  monto_contribuido: num(),
  saldo_restante: z.coerce.number().int(),
  liquidacion_especifica_numero: z.coerce.number().int().nullish(),
  comprobante_activo: comprobanteMinimalSchema.nullish(),
  // Financial fields from backend
  honorarios: num().nullable().optional(),
  descuento: num().nullable().optional(),
  sub_total: num().nullable().optional(),
  // Dates
  fecha_revision: z.string().nullish(),
  fecha_presentacion: z.string().nullish(),
  dictamen_revision: z.string().nullish(),
});

export const rhInspectorMensualTotalesSchema = z.object({
  inspecciones_programadas: z.coerce.number().int(),
  inspecciones_liquidadas: z.coerce.number().int(),
  inspecciones_pagadas_hasta_mes_anterior: z.coerce.number().int(),
  saldo_restante: z.coerce.number().int(),
  sub_total: num(),
  descuento: num(),
  honorarios: num(),
  tasa_descuento_aplicada: num(),
});

/** Rango de descuento — mirror of backend RangoDescuentoOut */
export const rangoDescuentoSchema = z.object({
  monto_minimo: num(),
  monto_maximo: num().nullish(),
  porcentaje_descuento: num(),
});

/** Variables de cálculo para el RH Inspector Mensual — escala de descuento aplicada */
export const rhInspectorVariablesCalculoSchema = z.object({
  escala_id: z.string(),
  escala_nombre: z.string(),
  rango_aplicado: rangoDescuentoSchema,
});

/** RHInspectorMensualListItemOut — matches backend schema exactly */
export const rhInspectorMensualListItemSchema = z.object({
  id: uuid(),
  periodo: z.number().int().nullish(),
  mes: z.number().int().nullish(),
  fecha_registro: z.string(),
  inspector: inspectorMinimalSchema,
  numero: z.number().nullable().optional(),
  totales: rhInspectorMensualTotalesSchema,
  detalles: z.array(rhInspectorMensualDetalleSchema),
  variables_calculo: rhInspectorVariablesCalculoSchema,
});

export type ReciboHonorarioInspectorMensual = z.infer<
  typeof rhInspectorMensualListItemSchema
>;
