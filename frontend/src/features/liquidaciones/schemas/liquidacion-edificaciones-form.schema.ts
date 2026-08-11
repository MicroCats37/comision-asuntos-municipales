/**
 * Zod schema for Edificaciones creation form.
 * General fields (proyecto, trámite, contacto) vienen del base compartido.
 */
import { z } from "zod";
import { generalFormSchema, proyectoFormSchema, contactoInlineSchema } from "./liquidacion-form-base.schema";

export const edificacionesFormSchema = z.object({
  ...proyectoFormSchema.shape,
  ...generalFormSchema.shape,
  // Especifica fields (motor PorcentajeObra)
  valor_declarado: z.number().positive("El valor declarado debe ser positivo"),
  // Smart Field outputs (set by Smart Fields via setValue)
  tarifas_ids: z.array(z.string()).optional(),
  // Contacto principal (singular, managed via ContactoFormModal)
  contacto: contactoInlineSchema.optional(),
});

export type EdificacionesFormData = z.infer<typeof edificacionesFormSchema>;
