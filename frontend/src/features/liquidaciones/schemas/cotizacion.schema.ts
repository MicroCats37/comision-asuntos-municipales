import { z } from "zod";

const num = () => z.coerce.number();

/** Detalle de cotización — POST /liquidaciones/{tipo}/cotizar */
export const CotizacionDetalleSchema = z.object({
  tarifa_id: z.string(),
  especialidad_id: z.string(),
  porcentaje_aplicado: num(),
  subtotal: num(),
});
export type CotizacionDetalle = z.infer<typeof CotizacionDetalleSchema>;

/** Output de cotización (PorcentajeObra) */
export const CotizacionOutputSchema = z.object({
  valor_declarado: num(),
  porcentaje_liquidacion: num(),
  derecho_minimo: num(),
  derecho_maximo: num().nullable(),
  porcentaje_minimo_uit: num(),
  derecho_aplicado_id: z.string(),
  detalles: z.array(CotizacionDetalleSchema),
  total_subtotal: num(),
  total: num(),
});
export type CotizacionOutput = z.infer<typeof CotizacionOutputSchema>;
