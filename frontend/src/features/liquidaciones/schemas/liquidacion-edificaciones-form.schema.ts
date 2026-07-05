/**
 * Zod schemas para formulario de liquidaciones edificaciones.
 */
import { z } from "zod";
import { tipoTramiteEdificacionesSchema } from "./liquidacion.schema";

// CIP: 3 to 6 digits
const cipSchema = z
  .string()
  .regex(/^\d{3,6}$/, "El CIP debe tener entre 3 y 6 dígitos");

// Especialidad ID: UUID
const especialidadIdSchema = z
  .string()
  .uuid("Debe seleccionar una especialidad");

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

// Proyecto Inline schema (para crear proyecto al vuelo)
export const proyectoInlineFormSchema = z
  .object({
    denominacion: z.string().min(1, "Denominación es requerida"),
    direccion: z.string().optional(),
    distrito_id: z.string().uuid("Distrito es requerido").optional(),
    entidad_id: z.string().uuid("Entidad es requerida").optional().nullable(),
    nombre_propietario: z.string().min(1, "Nombre del propietario es requerido"),
    entidad: z.object({
      tipo_documento: z.enum(["RUC", "DNI"], {
        message: "Tipo de documento es requerido",
      }),
      numero_documento: z.string().min(1, "Número de documento es requerido"),
      razon_social: z.string().min(1, "Razón social o nombre completo es requerido"),
    }),
  })
  .refine(
    (data) => {
      // Si tipo_documento es RUC, numero_documento debe tener 11 dígitos
      // Si es DNI, debe tener 8 dígitos
      const numDoc = data.entidad.numero_documento;
      if (data.entidad.tipo_documento === "RUC") {
        return /^\d{11}$/.test(numDoc);
      } else if (data.entidad.tipo_documento === "DNI") {
        return /^\d{8}$/.test(numDoc);
      }
      return true;
    },
    {
      message: "El número de documento no tiene la longitud correcta para el tipo seleccionado",
      path: ["entidad", "numero_documento"],
    },
  );

export type ProyectoInlineFormSchema = z.infer<typeof proyectoInlineFormSchema>;

export const liquidacionEdificacionFormSchema = z.object({
  municipalidad_id: z.string().uuid("Debe seleccionar una municipalidad"),
  tipo_tramite: tipoTramiteEdificacionesSchema,
  valor_proyecto: z
    .number()
    .positive("El valor del proyecto debe ser positivo"),
  expediente: z.string().optional(),
  valor_base_calculo: z.number().optional(),
  observacion: z.string().optional(),
  revisiones_ids: z.array(z.string()),
  proyectistas: z.array(proyectistaInlineSchema),
  contactos: z.array(contactoInlineSchema),
  // TODO: delegada ya no se envía en creación — se hará por endpoint separado
  delegados_ids: z.array(z.string()).optional(),
  proyecto_public_id: z.string().optional(),
  proyecto_inline: proyectoInlineFormSchema.optional(),
  tarifas_ids: z.array(z.string().uuid()).optional(),
});

export type LiquidacionEdificacionFormSchema = z.infer<
  typeof liquidacionEdificacionFormSchema
>;

// Schema for submit — soporta proyecto_public_id O proyecto_inline
// delegador_ids fue eliminado del payload de creación
export const liquidacionEdificacionSubmitSchema = z
  .object({
    proyecto_public_id: z.string().optional(),
    proyecto_inline: proyectoInlineFormSchema.optional(),
    municipalidad_id: z.string().uuid("Debe seleccionar una municipalidad"),
    tipo_tramite: tipoTramiteEdificacionesSchema,
    valor_proyecto: z
      .number()
      .positive("El valor del proyecto debe ser positivo"),
    expediente: z.string().optional(),
    valor_base_calculo: z.number().optional(),
    observacion: z.string().optional(),
    revisiones_ids: z.array(z.string()).default([]),
    proyectistas: z.array(proyectistaInlineSchema).default([]),
    contactos: z.array(contactoInlineSchema).default([]),
    tarifas_ids: z.array(z.string().uuid()).default([]),
  })
  .refine(
    (data) =>
      (data.proyecto_public_id && !data.proyecto_inline) ||
      (!data.proyecto_public_id && data.proyecto_inline),
    {
      message:
        "Debe proporcionar proyecto_public_id O proyecto_inline, nunca ambos",
    },
  );

export type LiquidacionEdificacionSubmitSchema = z.infer<
  typeof liquidacionEdificacionSubmitSchema
>;

// Schema for CIP validation (used in ProyectistaFormModal)
export const cipValidationSchema = z.object({
  cip: cipSchema,
});
