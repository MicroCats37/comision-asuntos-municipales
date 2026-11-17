import { z } from "zod";

// Coerce helper: backend may send Decimal as string ("123.45") or number
const num = () => z.coerce.number();

// Inspector asignado a una IO (liquidacion_tipo.inspectores[])
export const PerfilIngenieroOutSchema = z.object({
  id: z.string(),
  cip: z.string(),
  dni: z.string().nullish(),
  nombres: z.string(),
  apellido_paterno: z.string(),
  apellido_materno: z.string(),
  nombre_completo: z.string(),
});

export const LiquidacionInspectorOutSchema = z.object({
  id: z.string(),
  inspector_id: z.string(),
  inspector_operacion_id: z.string().nullish(),
  perfil_ingeniero: PerfilIngenieroOutSchema,
  numero_registro: z.string().nullish(),
  categoria: z.string().nullish(),
  periodo: z.number().int().nullish(),
  mes: z.number().int().nullish(),
  dictamen_revision: z.string().nullish(),
});

// RegistroPagoOut (registros_pago[] inside VisitasDatosOut)
export const RegistroPagoOutSchema = z.object({
  id: z.string(),
  periodo: z.number().int().nullish(),
  mes: z.number().int().nullish(),
  inspecciones_pagadas: z.coerce.number().int(),
  fecha_registro: z.string().nullish(),
});

// ContinuidadVisitasOut — fila de continuidad de la IO (liquidacion_tipo.continuidad)
// monto_acumulado/total_acumulado = valor completo del trabajo
// subtotal_credito/total_credito = crédito de la liquidación previa
// La diferencia a cobrar es liquidacion_general.sub_total / total
export const ContinuidadVisitasOutSchema = z.object({
  id: z.string(),
  liquidacion_previa_id: z.string().nullish(),
  monto_acumulado: num(),
  total_acumulado: num(),
  subtotal_credito: num(),
  total_credito: num(),
  visitas_previas_totales: z.coerce.number().int().nullish(),
  visitas_previas_pendientes: z.coerce.number().int().nullish(),
  categoria_previa: z.string().nullish(),
  observacion: z.string().nullish(),
});

// VisitasDatosOut (Inspeccion Obra):
// id, cantidad_visitas, porcentaje_uit, categoria, tarifa_aplicada_id, inspectores, registros_pago
export const VisitasDatosOutSchema = z.object({
  id: z.string(),
  cantidad_visitas: z.coerce.number().int(),
  porcentaje_uit: num().nullish(),
  categoria: z.string().nullish(),
  tarifa_aplicada_id: z.string().nullish(),
  inspectores: z.array(LiquidacionInspectorOutSchema).default([]),
  registros_pago: z.array(RegistroPagoOutSchema).default([]),
  continuidad: ContinuidadVisitasOutSchema.nullish(),
});

export type VisitasDatosOut = z.infer<typeof VisitasDatosOutSchema>;
export type ContinuidadVisitasOut = z.infer<typeof ContinuidadVisitasOutSchema>;
export type RegistroPagoOut = z.infer<typeof RegistroPagoOutSchema>;
export type PerfilIngenieroOut = z.infer<typeof PerfilIngenieroOutSchema>;
export type LiquidacionInspectorOut = z.infer<
  typeof LiquidacionInspectorOutSchema
>;
