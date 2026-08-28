import { z } from "zod";

// Coerce helper: backend may send Decimal as string ("123.45") or number
const num = () => z.coerce.number();

// M2DatosOut (Mecanica Suelos, Habilitacion Urbana):
// id, area_m2, costo_por_m2, derecho_minimo, derecho_maximo, tarifa_aplicada_id, derecho_aplicado_id
export const M2DatosOutSchema = z.object({
  id: z.string(),
  area_m2: num(),
  costo_por_m2: num(),
  derecho_minimo: num().nullish(),
  derecho_maximo: num().nullish(),
  tarifa_aplicada_id: z.string(),
  derecho_aplicado_id: z.string(),
});

export type M2DatosOut = z.infer<typeof M2DatosOutSchema>;
