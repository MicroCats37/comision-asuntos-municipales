import { z } from "zod";

// Coerce helper: backend may send Decimal as string ("123.45") or number
const num = () => z.coerce.number();

// Inspector asignado a una IO (liquidacion_tipo.inspectores[])
export const PerfilIngenieroOutSchema = z.object({
  id: z.string(),
  cip: z.string(),
  dni: z.string(),
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

// VisitasDatosOut (Inspeccion Obra):
// id, cantidad_visitas, porcentaje_uit, categoria, tarifa_aplicada_id, inspectores
export const VisitasDatosOutSchema = z.object({
  id: z.string(),
  cantidad_visitas: z.coerce.number().int(),
  porcentaje_uit: num(),
  categoria: z.string(),
  tarifa_aplicada_id: z.string(),
  inspectores: z.array(LiquidacionInspectorOutSchema).default([]),
});

export type VisitasDatosOut = z.infer<typeof VisitasDatosOutSchema>;
export type PerfilIngenieroOut = z.infer<typeof PerfilIngenieroOutSchema>;
export type LiquidacionInspectorOut = z.infer<
  typeof LiquidacionInspectorOutSchema
>;
