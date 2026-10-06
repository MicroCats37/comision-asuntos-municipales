import { z } from "zod";
import {
  LiquidacionGeneralOutputSchema,
  LiquidacionTipoOutputSchema,
  paginatedResponseSchema,
} from "./liquidacion-base.schema";
import { M2DatosOutSchema } from "./liquidacion-m2.schema";

// Mecanica Suelos (M2)
export const liquidacionMecanicaSuelosListItemSchema = z.object({
  liquidacion_general: LiquidacionGeneralOutputSchema,
  liquidacion_especifica: LiquidacionTipoOutputSchema,
  liquidacion_tipo: M2DatosOutSchema,
});
export const liquidacionMecanicaSuelosPaginatedSchema = paginatedResponseSchema(
  liquidacionMecanicaSuelosListItemSchema,
);
export type LiquidacionMecanicaSuelosListItem = z.infer<
  typeof liquidacionMecanicaSuelosListItemSchema
>;
