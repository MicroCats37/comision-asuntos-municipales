import { z } from 'zod';

// M2DatosOut (Mecanica Suelos, Habilitacion Urbana):
// id, area_m2, costo_por_m2, derecho_minimo, derecho_maximo, tarifa_aplicada_id, derecho_aplicado_id
export const M2DatosOutSchema = z.object({
  id: z.string(),
  area_m2: z.number(),
  costo_por_m2: z.number(),
  derecho_minimo: z.number(),
  derecho_maximo: z.number(),
  tarifa_aplicada_id: z.string(),
  derecho_aplicado_id: z.string(),
});

export type M2DatosOut = z.infer<typeof M2DatosOutSchema>;
