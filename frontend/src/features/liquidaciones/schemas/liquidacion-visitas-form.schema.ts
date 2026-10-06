/**
 * Zod schema for Visitas creation forms (Inspeccion Obra).
 * Uses cantidad_visitas + categoria + tarifa_visitas_id.
 */
import { z } from "zod";
import {
  contactoInlineSchema,
  generalFormSchema,
  proyectoFormSchema,
} from "./liquidacion-form-base.schema";

export const visitasFormSchema = z.object({
  ...proyectoFormSchema.shape,
  ...generalFormSchema.shape,
  // Tipo de liquidación (seleccionable via selectSearchable). NO se envía
  // al backend — se usa solo en frontend para filtrar el modal de inspectores.
  tipo_liquidacion_id: z.string().optional(),
  // Especifica fields
  cantidad_visitas: z
    .number()
    .int()
    .positive("La cantidad de visitas debe ser positiva")
    .max(9999, "La cantidad de visitas excede el máximo permitido"),
  categoria: z.enum(["C1", "C2", "C3", "C4"], {
    message: "Categoría es requerida",
  }),
  // Smart Field outputs (set by Smart Fields via setValue)
  tarifa_visitas_id: z.string().optional(),
  // Contacto (used in edit modal — not in creation form)
  contacto: contactoInlineSchema.optional(),
  // Inspector operacion ID (optional, for reassigning inspector in edit)
  inspector_operacion_id: z.string().optional(),
  // Inspector seleccionado (form de creación sin previa)
  inspector_id: z.string().optional(),
});

export type VisitasFormData = z.infer<typeof visitasFormSchema>;
