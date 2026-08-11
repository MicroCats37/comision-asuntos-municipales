import { z } from 'zod';

// Coerce helper: backend may send Decimal as string ("123.45") or number
const num = () => z.coerce.number();

// VisitasDatosOut (Inspeccion Obra):
// id, cantidad_visitas, porcentaje_uit, categoria, tarifa_aplicada_id
export const VisitasDatosOutSchema = z.object({
  id: z.string(),
  cantidad_visitas: z.coerce.number().int(),
  porcentaje_uit: num(),
  categoria: z.string(),
  tarifa_aplicada_id: z.string(),
});

export type VisitasDatosOut = z.infer<typeof VisitasDatosOutSchema>;
