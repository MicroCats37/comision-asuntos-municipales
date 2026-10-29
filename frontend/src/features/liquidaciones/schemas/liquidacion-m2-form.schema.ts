/**
 * Zod schema for M2 creation forms (Habilitacion Urbana, Mecanica Suelos).
 * Uses area_solicitada + tarifa_m2_id.
 */
import { z } from "zod";
import {
  contactoInlineSchema,
  generalFormSchema,
  numeroRevisionFormSchema,
  proyectoFormSchema,
} from "./liquidacion-form-base.schema";

export const m2FormSchema = z.object({
  ...proyectoFormSchema.shape,
  ...generalFormSchema.shape,
  // Número de revisión — etiqueta editable (1, 3 o 5)
  ...numeroRevisionFormSchema.shape,
  // Especifica fields
  area_solicitada: z
    .number({
      error: (issue) =>
        issue.input === undefined || issue.input === null || issue.input === ""
          ? "El área solicitada es requerida"
          : "El área solicitada debe ser un número válido",
    })
    .positive("El área solicitada debe ser positiva")
    .max(9999999999.99, "El área solicitada excede el máximo permitido")
    .finite("El área solicitada debe ser un número válido"),
  // Smart Field outputs (set by Smart Fields via setValue)
  tarifa_m2_id: z.string().optional(),
  // Contacto principal (singular, managed via ContactoFormModal)
  contacto: contactoInlineSchema.optional(),
});

export type M2FormData = z.infer<typeof m2FormSchema>;
