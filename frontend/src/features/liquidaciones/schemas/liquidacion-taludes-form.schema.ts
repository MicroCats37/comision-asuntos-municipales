/**
 * Zod schema for Taludes creation form (PorcentajeObra motor).
 * Estructura idéntica a Edificaciones/Impacto Vial, con nombre propio
 * para que cada tipo sea independiente.
 */
import { z } from "zod";
import {
  contactoInlineSchema,
  generalFormSchema,
  proyectoFormSchema,
} from "./liquidacion-form-base.schema";

export const taludesFormSchema = z.object({
  ...proyectoFormSchema.shape,
  ...generalFormSchema.shape,
  // Especifica fields
  valor_declarado: z.number().positive("El valor declarado debe ser positivo"),
  // Smart Field outputs — set by Smart Fields via setValue
  /** ID de la única tarifa vigente de porcentaje de obra */
  tarifa_unica_id: z.string().optional(),
  /** IDs de especialidades seleccionadas por el usuario */
  especialidades_seleccionadas: z.array(z.string()).optional(),
  // Contacto principal (singular, managed via ContactoFormModal)
  contacto: contactoInlineSchema.optional(),
});

export type TaludesFormData = z.infer<typeof taludesFormSchema>;
