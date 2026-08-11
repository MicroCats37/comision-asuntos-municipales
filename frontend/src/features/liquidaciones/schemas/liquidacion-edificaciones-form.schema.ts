/**
 * Zod schema for Edificaciones creation form.
 * Matches the Smart Field architecture where each field is self-contained.
 */
import { z } from "zod";
import { generalFormSchema, proyectoFormSchema } from "./liquidacion-form-base.schema";

// Contacto inline schema — matches backend ContactoInlineSchema (SINGLE contacto, no array)
export const contactoInlineSchema = z.object({
  nombres: z.string().min(1, "Los nombres son requeridos"),
  apellidos: z.string().optional(),
  dni: z.string().optional(),
  cargo: z.string().optional(),
  telefono: z.string().optional(),
  celular: z.string().optional(),
  email: z.string().email("Email inválido").optional().or(z.literal("")),
});

export type ContactoInline = z.infer<typeof contactoInlineSchema>;

export const edificacionesFormSchema = z.object({
  ...proyectoFormSchema.shape,
  ...generalFormSchema.shape,
  // Especifica fields
  valor_declarado: z.number().positive("El valor declarado debe ser positivo"),
  // Smart Field outputs (set by Smart Fields via setValue)
  tarifas_ids: z.array(z.string()).optional(),
  // Contacto principal (singular, managed via ContactoFormModal)
  contacto: contactoInlineSchema.optional(),
});

export type EdificacionesFormData = z.infer<typeof edificacionesFormSchema>;
