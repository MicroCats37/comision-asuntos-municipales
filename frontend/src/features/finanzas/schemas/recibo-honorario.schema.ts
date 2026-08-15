/**
 * Zod schemas for Recibos de Honorarios — mirrors backend ReciboHonorarioDelegadoOut.
 * Endpoint: GET /finanzas/recibos-honorarios, POST /finanzas/recibos-honorarios
 */
import { z } from "zod";

const uuid = () => z.string();
const num = () => z.coerce.number();

export const tipoLiquidacionMinimalSchema = z.object({
  codigo: z.string(),
  nombre: z.string(),
});

export const liquidacionGeneralMinimalSchema = z.object({
  id: uuid(),
  expediente: z.string().nullish(),
  numero_revision: z.coerce.number().int(),
  sub_total: num(),
  total: num(),
  fecha_registro: z.string(),
  tipo_liquidacion: tipoLiquidacionMinimalSchema.nullish(),
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

/** ReciboHonorarioDelegadoOut — matches backend schema exactly */
export const reciboHonorarioDelegadoSchema = z.object({
  id: uuid(),
  liquidacion_delegado_id: uuid(),
  liquidacion_general: liquidacionGeneralMinimalSchema,
  delegado: delegadoMinimalSchema,
  especialidad: especialidadMinimalSchema,
  sub_total: num(),
  imp_bruto: num(),
  renta_cip: num(),
  aporte_codemu: num(),
  fondo_comun: num(),
  neto_honorario: num(),
  honorario: num(),
  created_at: z.string(),
});

export type ReciboHonorarioDelegado = z.infer<
  typeof reciboHonorarioDelegadoSchema
>;
