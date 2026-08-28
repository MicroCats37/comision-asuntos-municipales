import { z } from "zod";
import {
  LiquidacionGeneralOutputSchema,
  LiquidacionTipoOutputSchema,
  paginatedResponseSchema,
} from "./liquidacion-base.schema";
import { PorcentajeObraDatosOutSchema } from "./liquidacion-porcentaje.schema";

// Edificaciones (PorcentajeObra)
export const liquidacionEdificacionesListItemSchema = z.object({
  liquidacion_general: LiquidacionGeneralOutputSchema,
  liquidacion_especifica: LiquidacionTipoOutputSchema,
  liquidacion_tipo: PorcentajeObraDatosOutSchema,
});
export const liquidacionEdificacionesPaginatedSchema = paginatedResponseSchema(
  liquidacionEdificacionesListItemSchema,
);
export type LiquidacionEdificacionesListItem = z.infer<
  typeof liquidacionEdificacionesListItemSchema
>;
