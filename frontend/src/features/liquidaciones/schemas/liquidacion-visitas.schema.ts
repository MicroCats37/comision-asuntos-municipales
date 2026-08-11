import { z } from 'zod';

// VisitasDatosOut (Inspeccion Obra):
// id, cantidad_visitas, porcentaje_uit, categoria, tarifa_aplicada_id
export const VisitasDatosOutSchema = z.object({
  id: z.string(),
  cantidad_visitas: z.number().int(),
  porcentaje_uit: z.number(),
  categoria: z.string(),
  tarifa_aplicada_id: z.string(),
});

export type VisitasDatosOut = z.infer<typeof VisitasDatosOutSchema>;
