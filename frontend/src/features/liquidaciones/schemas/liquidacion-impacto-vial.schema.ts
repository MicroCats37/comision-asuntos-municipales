import { z } from "zod";
import {
  LiquidacionGeneralOutputSchema,
  LiquidacionTipoOutputSchema,
  paginatedResponseSchema,
} from "./liquidacion-base.schema";
import { PorcentajeObraDatosOutSchema } from "./liquidacion-porcentaje.schema";

// Impacto Vial (PorcentajeObra)
export const liquidacionImpactoVialListItemSchema = z.object({
  liquidacion_general: LiquidacionGeneralOutputSchema,
  liquidacion_especifica: LiquidacionTipoOutputSchema,
  liquidacion_tipo: PorcentajeObraDatosOutSchema,
});
export const liquidacionImpactoVialPaginatedSchema = paginatedResponseSchema(
  liquidacionImpactoVialListItemSchema,
);
export type LiquidacionImpactoVialListItem = z.infer<
  typeof liquidacionImpactoVialListItemSchema
>;
