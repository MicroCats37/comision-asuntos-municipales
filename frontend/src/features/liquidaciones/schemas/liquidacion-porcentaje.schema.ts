import { z } from "zod";

// Coerce helper: backend may send Decimal as string ("123.45") or number
const num = () => z.coerce.number();

// PorcentajeObraDetalleOut: id, tarifa_aplicada_id, especialidad_id, porcentaje_aplicado, subtotal, igv, uit, total
export const PorcentajeObraDetalleOutSchema = z.object({
  id: z.string(),
  tarifa_aplicada_id: z.string(),
  especialidad_id: z.string(),
  porcentaje_aplicado: num(),
  subtotal: num(),
});

// PorcentajeObraDatosOut (Edificaciones, Taludes, Impacto Vial):
// id, valor_declarado, porcentaje_liquidacion, tipo_tramite?, derecho_minimo?, derecho_maximo?,
// porcentaje_minimo_uit, derecho_aplicado_id, detalles: [{...}]
export const PorcentajeObraDatosOutSchema = z.object({
  id: z.string(),
  valor_declarado: num(),
  porcentaje_liquidacion: num(),
  tipo_tramite: z.string().nullish(),
  derecho_minimo: num().nullish(),
  derecho_maximo: num().nullish(),
  porcentaje_minimo_uit: num(),
  derecho_aplicado_id: z.string(),
  detalles: z.array(PorcentajeObraDetalleOutSchema),
});

export type PorcentajeObraDetalleOut = z.infer<
  typeof PorcentajeObraDetalleOutSchema
>;
export type PorcentajeObraDatosOut = z.infer<
  typeof PorcentajeObraDatosOutSchema
>;
