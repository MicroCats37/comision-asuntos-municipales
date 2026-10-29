import { z } from "zod";

const num = () => z.coerce.number();

/**
 * Detalle de cotización — POST /liquidaciones/{tipo}/cotizar
 *
 * `porcentaje_aplicado` es NULL en la estrategia TOTAL_EXPLICITO (los
 * porcentajes quedan NULL) y `especialidad` puede venir ausente.
 */
export const CotizacionDetalleSchema = z.object({
  tarifa_id: z.string().nullish(),
  especialidad: z
    .object({
      id: z.string(),
      nombre: z.string(),
    })
    .nullish(),
  porcentaje_aplicado: num().nullable(),
  subtotal: num(),
});
export type CotizacionDetalle = z.infer<typeof CotizacionDetalleSchema>;

/**
 * Proyección efímera de la diferencia padre - detalles.
 * El preview NUNCA la persiste (es una proyección, no un dato guardado).
 */
export const CotizacionAcumulacionSchema = z.object({
  porcentaje_acumulado: num().nullable(),
  subtotal_acumulado: num(),
});
export type CotizacionAcumulacion = z.infer<typeof CotizacionAcumulacionSchema>;

/**
 * Output de cotización (PorcentajeObra).
 *
 * Los campos de estrategia (`estrategia_cotizacion`, `count_habilitadas`,
 * `total_explicito`, `porcentaje_tarifa`, `acumulacion`) SOLO llegan en
 * Edificaciones: el resto de motores PO no exponen campos de estrategia y los
 * declaramos opcionales para no romper su contrato.
 */
export const CotizacionOutputSchema = z.object({
  valor_declarado: num().nullish(),
  porcentaje_liquidacion: num().nullish(),
  derecho_minimo: num().nullish(),
  derecho_maximo: num().nullish(),
  porcentaje_minimo_uit: num().nullish(),
  derecho_aplicado_id: z.string().nullish(),
  estrategia_cotizacion: z.string().nullish(),
  count_habilitadas: z.number().int().nullish(),
  total_explicito: num().nullish(),
  porcentaje_tarifa: num().nullish(),
  acumulacion: CotizacionAcumulacionSchema.nullish(),
  detalles: z.array(CotizacionDetalleSchema),
  total_subtotal: num(),
  total: num(),
});
export type CotizacionOutput = z.infer<typeof CotizacionOutputSchema>;
