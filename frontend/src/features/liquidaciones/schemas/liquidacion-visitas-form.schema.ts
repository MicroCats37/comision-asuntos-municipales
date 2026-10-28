/**
 * Zod schema for Visitas creation forms (Inspeccion Obra).
 * Keeps categoria as derived visual state; backend payloads use tarifa_visitas_id.
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
    .number({
      error: (issue) =>
        issue.input === undefined || issue.input === null || issue.input === ""
          ? "La cantidad de visitas es requerida"
          : "La cantidad de visitas debe ser un número válido",
    })
    .int("La cantidad de visitas debe ser un número entero")
    .positive("La cantidad de visitas debe ser positiva")
    .max(9999, "La cantidad de visitas excede el máximo permitido"),
  categoria: z.enum(["1", "2", "3", "4"], {
    message: "Categoría es requerida",
  }),
  // Smart Field outputs (set by Smart Fields via setValue)
  tarifa_visitas_id: z.string().min(1, "No se pudo cargar la tarifa vigente"),
  // Contacto (used in edit modal — not in creation form)
  contacto: contactoInlineSchema.optional(),
  // InspectorOperacion seleccionado para crear IO. El backend deriva el inspector desde esta operación.
  inspector_operacion_id: z.string().min(1, "Selecciona un inspector"),
  // Inspector seleccionado, usado solo como estado visual del selector.
  inspector_id: z.string().optional(),
});

export type VisitasFormData = z.infer<typeof visitasFormSchema>;
