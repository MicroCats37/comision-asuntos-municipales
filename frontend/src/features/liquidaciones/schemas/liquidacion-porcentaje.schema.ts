import { z } from 'zod';

// PorcentajeObraDetalleOut: id, tarifa_aplicada_id, especialidad_id, porcentaje_aplicado, subtotal, igv, uit, total
export const PorcentajeObraDetalleOutSchema = z.object({
  id: z.string(),
  tarifa_aplicada_id: z.string(),
  especialidad_id: z.string(),
  porcentaje_aplicado: z.number(),
  subtotal: z.number(),
  igv: z.number(),
  uit: z.number(),
  total: z.number(),
});

// PorcentajeObraDatosOut (Edificaciones, Taludes, Impacto Vial):
// id, valor_declarado, porcentaje_liquidacion, tipo_tramite?, derecho_minimo?, derecho_maximo?,
// porcentaje_minimo_uit, derecho_aplicado_id, detalles: [{...}]
export const PorcentajeObraDatosOutSchema = z.object({
  id: z.string(),
  valor_declarado: z.number(),
  porcentaje_liquidacion: z.number(),
  tipo_tramite: z.string().optional(),
  derecho_minimo: z.number().optional(),
  derecho_maximo: z.number().optional(),
  porcentaje_minimo_uit: z.number(),
  derecho_aplicado_id: z.string(),
  detalles: z.array(PorcentajeObraDetalleOutSchema),
});

export type PorcentajeObraDetalleOut = z.infer<typeof PorcentajeObraDetalleOutSchema>;
export type PorcentajeObraDatosOut = z.infer<typeof PorcentajeObraDatosOutSchema>;
