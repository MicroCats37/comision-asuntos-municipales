/**
 * Zod schema for Visitas creation forms (Inspeccion Obra).
 * Uses cantidad_visitas + categoria + tarifa_visitas_id.
 */
import { z } from "zod";
import {
  generalFormSchema,
  proyectoFormSchema,
} from "./liquidacion-form-base.schema";

export const visitasFormSchema = z.object({
  ...proyectoFormSchema.shape,
  ...generalFormSchema.shape,
  // Especifica fields
  cantidad_visitas: z
    .number()
    .int()
    .positive("La cantidad de visitas debe ser positiva"),
  categoria: z.enum(["C1", "C2", "C3", "C4"], {
    message: "Categoría es requerida",
  }),
  // Smart Field outputs (set by Smart Fields via setValue)
  tarifa_visitas_id: z.string().optional(),
});

export type VisitasFormData = z.infer<typeof visitasFormSchema>;
