/**
 * Zod schema for Habilitacion Urbana creation form (M2 motor).
 * Estructura idéntica a Mecanica Suelos, con nombre propio.
 */
import { z } from "zod";
import {
  contactoInlineSchema,
  generalFormSchema,
  numeroRevisionFormSchema,
  proyectoFormSchema,
} from "./liquidacion-form-base.schema";

export const habilitacionUrbanaFormSchema = z.object({
  ...proyectoFormSchema.shape,
  ...generalFormSchema.shape,
  // Número de revisión — etiqueta editable (1, 3 o 5)
  ...numeroRevisionFormSchema.shape,
  // Especifica fields
  area_solicitada: z
    .number()
    .positive("El área solicitada debe ser positiva")
    .max(9999999999.99, "El área solicitada excede el máximo permitido")
    .finite(),
  // Smart Field outputs (set by Smart Fields via setValue)
  tarifa_m2_id: z.string().min(1, "No se pudo cargar la tarifa vigente"),
  // Contacto principal (singular, managed via ContactoFormModal)
  contacto: contactoInlineSchema.optional(),
});

export type HabilitacionUrbanaFormData = z.infer<
  typeof habilitacionUrbanaFormSchema
>;
