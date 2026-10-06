import { z } from "zod";
import {
  LiquidacionGeneralOutputSchema,
  LiquidacionTipoOutputSchema,
  paginatedResponseSchema,
} from "./liquidacion-base.schema";
import { PorcentajeObraDatosOutSchema } from "./liquidacion-porcentaje.schema";

// Taludes (PorcentajeObra)
export const liquidacionTaludesListItemSchema = z.object({
  liquidacion_general: LiquidacionGeneralOutputSchema,
  liquidacion_especifica: LiquidacionTipoOutputSchema,
  liquidacion_tipo: PorcentajeObraDatosOutSchema,
});
export const liquidacionTaludesPaginatedSchema = paginatedResponseSchema(
  liquidacionTaludesListItemSchema,
);
export type LiquidacionTaludesListItem = z.infer<
  typeof liquidacionTaludesListItemSchema
>;
