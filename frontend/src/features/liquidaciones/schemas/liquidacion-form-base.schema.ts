import { z } from "zod";

// Shared proyecto fields used in all 6 create forms
export const proyectoFormSchema = z.object({
  denominacion: z.string().min(1, "Requerido"),
  nombre_propietario: z.string().min(1, "Requerido"),
  direccion: z.string().min(1, "Requerido"),
  distrito_id: z.string().min(1, "Requerido"),
  entidad_tipo_documento: z.enum(["RUC", "DNI"]),
  entidad_numero_documento: z.string().min(1, "Requerido"),
  entidad_razon_social: z.string().min(1, "Requerido"),
});

// Shared liquidacion_general fields used in all 6 create forms
export const generalFormSchema = z.object({
  municipalidad_id: z.string().min(1, "Requerido"),
  expediente: z.string().min(1, "Requerido"),
  observacion: z.string().optional(),
  retencion: z.boolean().optional(),
});
