import { z } from "zod";
import { esNumeroRevisionValido } from "../utils/numeroRevision";

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
  distrito_id: z.string().optional().or(z.literal("")),
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
});

/**
 * Bloque compartido del número de revisión.
 *
 * Espejo del contrato backend `NumeroRevisionRequeridoMixin`: obligatorio y
 * acotado al conjunto permitido {1, 3, 5}. El número de revisión es una
 * ETIQUETA EDITABLE elegida por el usuario — el backend no lo deriva.
 *
 * Solo lo componen los CINCO tipos con revisión editable (Edificaciones,
 * Habilitación Urbana, Mecánica de Suelos, Taludes, Impacto Vial).
 * Inspección de Obra es revision-less: su schema NO incluye este bloque y el
 * backend mantiene su liquidación fija en revisión 1.
 */
export const numeroRevisionFormSchema = z.object({
  numero_revision: z
    .number({
      error: (issue) =>
        issue.input === undefined || issue.input === null || issue.input === ""
          ? "El número de revisión es requerido"
          : "El número de revisión debe ser un número válido",
    })
    .int("El número de revisión debe ser un entero")
    .refine(
      (valor) => esNumeroRevisionValido(valor),
      "El número de revisión debe ser 1, 3 o 5",
    ),
});
