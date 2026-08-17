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
  dni: z.string(),
  nombre_completo: z.string(),
});

export const especialidadMinimalSchema = z.object({
  id: uuid(),
  codigo: z.string(),
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
