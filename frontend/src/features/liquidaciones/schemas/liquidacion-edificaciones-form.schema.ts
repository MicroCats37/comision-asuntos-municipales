/**
 * Zod schema for Edificaciones creation form.
 * Matches the Smart Field architecture where each field is self-contained.
 */
import { z } from "zod";
import { generalFormSchema, proyectoFormSchema } from "./liquidacion-form-base.schema";

export const edificacionesFormSchema = z.object({
  ...proyectoFormSchema.shape,
  ...generalFormSchema.shape,
  // Especifica fields
  valor_declarado: z.number().positive("El valor declarado debe ser positivo"),
  // Smart Field outputs (set by Smart Fields via setValue)
  tarifas_ids: z.array(z.string()).optional(),
});

export type EdificacionesFormData = z.infer<typeof edificacionesFormSchema>;
