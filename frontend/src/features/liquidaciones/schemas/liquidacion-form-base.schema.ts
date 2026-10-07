import { z } from "zod";

// Contacto inline schema — matches backend ContactoInlineSchema (SINGLE contacto)
// GENERAL: se usa en los 6 tipos de liquidación.
//
// NOTA: Zod v4 ignora `{ required_error, invalid_type_error }` (esa es API v3).
// La API unificada es `{ error }` — cubre required + invalid_type en uno.
export const contactoInlineSchema = z.object({
  nombres: z
    .string({ error: "Los nombres son requeridos" })
    .min(1, "Los nombres son requeridos"),
  apellidos: z.string().optional(),
  dni: z.string().optional(),
  cargo: z.string().optional(),
  telefono: z.string().optional(),
  celular: z.string().optional(),
  email: z
    .string({ error: "Email inválido" })
    .email("Email inválido")
    .optional()
    .or(z.literal("")),
});

export type ContactoInline = z.infer<typeof contactoInlineSchema>;

// Shared proyecto fields used in all 6 create forms.
// `error` en Zod v4 actúa como required_error + invalid_type_error unificado
// → un campo vacío o undefined se muestra al usuario como "Requerido", no
// como el default "Invalid input: expected string, received undefined".
export const proyectoFormSchema = z.object({
  denominacion: z.string().optional(),
  nombre_propietario: z.string({ error: "Requerido" }).min(1, "Requerido"),
  direccion: z.string({ error: "Requerido" }).min(1, "Requerido"),
  distrito_id: z
    .string({ error: "Requerido" })
    .min(1, "Requerido"),
  urbanizacion: z.string().optional(),
  entidad_tipo_documento: z.enum(["RUC", "DNI"]).optional().or(z.literal("")),
  entidad_numero_documento: z
    .string({ error: "Requerido" })
    .min(1, "Requerido"),
  entidad_razon_social: z.string({ error: "Requerido" }).min(1, "Requerido"),
});

// Shared liquidacion_general fields used in all 6 create forms
export const generalFormSchema = z.object({
  municipalidad_id: z.string({ error: "Requerido" }).min(1, "Requerido"),
  expediente: z.string().optional(),
  observacion: z.string().optional(),
  retencion: z.boolean().optional(),
});
