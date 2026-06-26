/**
 * Zod schemas para formulario de liquidaciones edificaciones.
 */
import { z } from "zod";
import { tipoTramiteEdificacionesSchema } from "./liquidacion.schema";

// CIP: 3 to 6 digits
const cipSchema = z.string().regex(/^\d{3,6}$/, "El CIP debe tener entre 3 y 6 dígitos");

// Especialidad ID: UUID
const especialidadIdSchema = z.string().uuid("Debe seleccionar una especialidad");

// Proyectista inline for submit
const proyectistaInlineSchema = z.object({
  cip: cipSchema,
  especialidad_id: especialidadIdSchema,
  descripcion: z.string().optional(),
});

// Contacto inline for submit — nombres and apellidos required, others optional
export const contactoInlineSchema = z.object({
  nombres: z.string().min(1, "Los nombres son requeridos"),
  apellidos: z.string().min(1, "Los apellidos son requeridos"),
  dni: z.string().optional(),
  telefono: z.string().optional(),
  celular: z.string().optional(),
  email: z.string().email("Email inválido").optional().or(z.literal("")),
  cargo: z.string().optional(),
  direccion: z.string().optional(),
  descripcion: z.string().optional(),
  principal: z.boolean().optional(),
});

export type ContactoInlineSchema = z.infer<typeof contactoInlineSchema>;

export const liquidacionEdificacionFormSchema = z.object({
  municipalidad_id: z.string().uuid("Debe seleccionar una municipalidad"),
  tipo_tramite: tipoTramiteEdificacionesSchema,
  valor_proyecto: z.number().positive("El valor del proyecto debe ser positivo"),
  observacion: z.string().optional(),
  revisiones_ids: z.array(z.string()),
  proyectistas: z.array(proyectistaInlineSchema),
  contactos: z.array(contactoInlineSchema),
  delegados_ids: z.array(z.string()),
  proyecto_public_id: z.string().min(1, "Debe seleccionar un proyecto"),
});

export type LiquidacionEdificacionFormSchema = z.infer<typeof liquidacionEdificacionFormSchema>;

// Schema for submit (excludes internal fields like proyecto that gets converted to public_id)
export const liquidacionEdificacionSubmitSchema = z.object({
  proyecto_public_id: z.string().min(1, "Debe seleccionar un proyecto"),
  municipalidad_id: z.string().uuid("Debe seleccionar una municipalidad"),
  tipo_tramite: tipoTramiteEdificacionesSchema,
  valor_proyecto: z.number().positive("El valor del proyecto debe ser positivo"),
  observacion: z.string().optional(),
  revisiones_ids: z.array(z.string()).default([]),
  proyectistas: z.array(proyectistaInlineSchema).default([]),
  contactos: z.array(contactoInlineSchema).default([]),
  delegados_ids: z.array(z.string()).default([]),
});

export type LiquidacionEdificacionSubmitSchema = z.infer<typeof liquidacionEdificacionSubmitSchema>;

// Schema for CIP validation (used in ProyectistaFormModal)
export const cipValidationSchema = z.object({
  cip: cipSchema,
});
