/**
 * Zod schema for M2 creation forms (Habilitacion Urbana, Mecanica Suelos).
 * Uses area_solicitada + tarifa_m2_id.
 */
import { z } from "zod";
import {
  contactoInlineSchema,
  generalFormSchema,
  proyectoFormSchema,
} from "./liquidacion-form-base.schema";

export const m2FormSchema = z.object({
  ...proyectoFormSchema.shape,
  ...generalFormSchema.shape,
  // Especifica fields
  area_solicitada: z.number().positive("El área solicitada debe ser positiva"),
  // Smart Field outputs (set by Smart Fields via setValue)
  tarifa_m2_id: z.string().optional(),
  // Contacto principal (singular, managed via ContactoFormModal)
  contacto: contactoInlineSchema.optional(),
});

export type M2FormData = z.infer<typeof m2FormSchema>;
