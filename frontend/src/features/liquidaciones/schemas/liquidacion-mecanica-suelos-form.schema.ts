/**
 * Zod schema for Mecanica Suelos creation form (M2 motor).
 * Estructura idéntica a Habilitacion Urbana, con nombre propio.
 */
import { z } from "zod";
import {
  contactoInlineSchema,
  generalFormSchema,
  proyectoFormSchema,
} from "./liquidacion-form-base.schema";

export const mecanicaSuelosFormSchema = z.object({
  ...proyectoFormSchema.shape,
  ...generalFormSchema.shape,
  // Especifica fields
  area_solicitada: z.number().positive("El área solicitada debe ser positiva"),
  // Smart Field outputs (set by Smart Fields via setValue)
  tarifa_m2_id: z.string().optional(),
  // Contacto principal (singular, managed via ContactoFormModal)
  contacto: contactoInlineSchema.optional(),
});

export type MecanicaSuelosFormData = z.infer<typeof mecanicaSuelosFormSchema>;
