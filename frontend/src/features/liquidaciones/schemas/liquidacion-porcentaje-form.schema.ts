/**
 * Zod schema for PorcentajeObra creation forms (Taludes, Impacto Vial).
 * Same structure as Edificaciones — uses valor_declarado + tarifas_ids.
 */
import { z } from "zod";
import {
  contactoInlineSchema,
  generalFormSchema,
  proyectoFormSchema,
} from "./liquidacion-form-base.schema";

export const porcentajeObraFormSchema = z.object({
  ...proyectoFormSchema.shape,
  ...generalFormSchema.shape,
  // Especifica fields
  valor_declarado: z.number().positive("El valor declarado debe ser positivo"),
  // Smart Field outputs (set by Smart Fields via setValue)
  tarifas_ids: z.array(z.string()).optional(),
  // Contacto principal (singular, managed via ContactoFormModal)
  contacto: contactoInlineSchema.optional(),
});

export type PorcentajeObraFormData = z.infer<typeof porcentajeObraFormSchema>;
