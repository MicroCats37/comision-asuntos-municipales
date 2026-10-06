import { z } from "zod";

export const TipoLiquidacionMinimalSchema = z.object({
  codigo: z.string(),
  nombre: z.string(),
});
export type TipoLiquidacionMinimal = z.infer<
  typeof TipoLiquidacionMinimalSchema
>;
