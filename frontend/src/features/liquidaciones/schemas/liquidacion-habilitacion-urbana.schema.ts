import { z } from "zod";
import {
  LiquidacionGeneralOutputSchema,
  LiquidacionTipoOutputSchema,
  paginatedResponseSchema,
} from "./liquidacion-base.schema";
import { M2DatosOutSchema } from "./liquidacion-m2.schema";

// Habilitacion Urbana (M2)
export const liquidacionHabilitacionUrbanaListItemSchema = z.object({
  liquidacion_general: LiquidacionGeneralOutputSchema,
  liquidacion_especifica: LiquidacionTipoOutputSchema,
  liquidacion_tipo: M2DatosOutSchema,
});
export const liquidacionHabilitacionUrbanaPaginatedSchema =
  paginatedResponseSchema(liquidacionHabilitacionUrbanaListItemSchema);
export type LiquidacionHabilitacionUrbanaListItem = z.infer<
  typeof liquidacionHabilitacionUrbanaListItemSchema
>;
