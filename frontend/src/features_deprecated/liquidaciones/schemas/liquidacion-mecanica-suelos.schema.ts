/**
 * Zod schemas para Mecánica de Suelos.
 * Endpoint base: /liquidaciones/mecanica-suelos
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";
import { contactoInlineSchema, proyectistaInlineSchema } from "./liquidacion-edificaciones-form.schema";

// ── Inner Schemas (data fields only) ──────────────────────────────────────────

/** Entidad inline para creación de proyecto inline */
const entidadInlineMecanicaSuelosSchema = z.object({
  tipo_documento: z.enum(["RUC", "DNI"], {
    message: "Tipo de documento es requerido",
  }),
  numero_documento: z.string().min(1, "Número de documento es requerido"),
  razon_social: z.string().min(1, "Razón social o nombre completo es requerido"),
});

/** Proyecto inline para creación en línea */
export const proyectoInlineMecanicaSuelosSchema = z.object({
  denominacion: z.string().min(1, "Denominación es requerida"),
  direccion: z.string().optional(),
  distrito_id: z.string().uuid("Distrito es requerido").optional(),
  nombre_propietario: z.string().min(1, "Nombre del propietario es requerido"),
  entidad: entidadInlineMecanicaSuelosSchema,
});

/** XOR: proyecto_public_id O proyecto_inline, nunca ambos ni ninguno */
export const proyectoXorMecanicaSuelosSchema = z
  .object({
    proyecto_public_id: z.string().optional(),
    proyecto_inline: proyectoInlineMecanicaSuelosSchema.optional(),
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

// ── Primera Revisión Schema ──────────────────────────────────────────────────

/**
 * Schema para primera revisión de Mecánica de Suelos.
 */
export const primeraRevisionMecanicaSuelosSchema = z.object({
  // XOR: uno de los dos es requerido
  proyecto_public_id: z.string().min(1, "Proyecto es requerido").optional(),
  proyecto_inline: proyectoInlineMecanicaSuelosSchema.optional(),
  municipalidad_id: z.string().uuid("Municipalidad es requerida"),
  area_solicitada: z.number().positive("El área debe ser positiva"),
  expediente: z.string().optional(),
  observacion: z.string().optional(),
  tarifas_ids: z.array(z.string().uuid()).min(1, "Debe seleccionar al menos una tarifa"),
  proyectistas: z.array(proyectistaInlineSchema).default([]),
  contactos: z.array(contactoInlineSchema).default([]),
});

export type PrimeraRevisionMecanicaSuelosData = z.infer<typeof primeraRevisionMecanicaSuelosSchema>;

// ── Cotizar Schemas ────────────────────────────────────────────────────────────

/** Payload para cotizar primera revisión — municipalidad NO requerida para cotizar; solo para creación final */
export const cotizarMecanicaSuelosPayloadSchema = z.object({
  area_solicitada: z.number().positive("El área debe ser positiva"),
  tarifas_ids: z.array(z.string().uuid()).min(1, "Debe seleccionar al menos una tarifa"),
});

/** Request para cotizar primera revisión */
export const cotizarMecanicaSuelosRequestSchema = z.object({
  liquidacion: cotizarMecanicaSuelosPayloadSchema,
});

// ── Cotizar Response Schemas ──────────────────────────────────────────────────

/** Totales en respuesta de cotización */
const cotizacionMecanicaSuelosTotalesSchema = z.object({
  subtotal: z.number(),
  igv: z.number(),
  total: z.number(),
  liquidacion_total: z.number(),
  total_a_pagar: z.number(),
});

/** Metadata en respuesta de cotización */
const cotizacionMecanicaSuelosMetadataSchema = z.object({
  igv_valor: z.number(),
  uit_valor: z.number(),
  area_solicitada: z.number().optional(),
});

/** Tarifa en respuesta de cotización */
const cotizacionMecanicaSuelosTarifaSchema = z.object({
  id: z.string(),
  costo_por_m2: z.number(),
  area_m2: z.number(),
  derecho_minimo: z.number(),
  derecho_maximo: z.number().nullable(),
});

/** Cálculo en respuesta de cotización */
const cotizacionMecanicaSuelosCalculoSchema = z.object({
  area_solicitada: z.number(),
  area_base_calculo: z.number(),
  derecho: z.number(),
  tarifa: cotizacionMecanicaSuelosTarifaSchema,
});

/** Payload de respuesta de cotización */
const cotizacionMecanicaSuelosPayloadSchema = z.object({
  numero_revision: z.number(),
  calculo_m2: cotizacionMecanicaSuelosCalculoSchema,
  totales: cotizacionMecanicaSuelosTotalesSchema,
  _metadata: cotizacionMecanicaSuelosMetadataSchema,
});

/** Wrapper para respuesta de cotización */
export const cotizacionMecanicaSuelosResponseSchema =
  apiResponseSchema(cotizacionMecanicaSuelosPayloadSchema);

// ── List Response Schemas ─────────────────────────────────────────────────────

// ── List Item Sub-schemas ─────────────────────────────────────────────────────

const proyectoListItemSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  nombre: z.string(),
  direccion: z.string().nullable(),
  valor_proyecto: z.number(),
  entidad: z.object({
    id: z.string().nullable(),
    tipo: z.string().nullable(),
    nombre: z.string().nullable(),
    ruc: z.string().nullable(),
  }),
});

const entidadListItemSchema = z.object({
  id: z.string().nullable(),
  tipo: z.string().nullable(),
  nombre: z.string().nullable(),
  ruc: z.string().nullable(),
});

const municipalidadListItemSchema = z.object({
  id: z.string(),
  nombre: z.string(),
  codigo: z.string().nullable(),
  provincia: z.null(),
  distrito: z.null(),
});

/** Schema for M2 list items — includes igv/total for percentage-based types */
const valoresM2ListItemSchema = z.object({
  subtotal: z.number(),
  igv: z.number(),
  total: z.number(),
  total_a_pagar: z.number(),
});

const proyectistaListItemSchema = z.object({
  id: z.string(),
  perfil_ingeniero_id: z.string().nullable(),
  perfil_ingeniero_nombres: z.string().nullable(),
  perfil_ingeniero_apellidos: z.string().nullable(),
  perfil_ingeniero_cip: z.string().nullable(),
  especialidad_id: z.string().nullable(),
  especialidad_nombre: z.string().nullable(),
  descripcion: z.string().nullable(),
});

const delegadoListItemSchema = z.object({
  id: z.string(),
  perfil_ingeniero_id: z.string().nullable(),
  perfil_ingeniero_nombres: z.string().nullable(),
  perfil_ingeniero_apellidos: z.string().nullable(),
  perfil_ingeniero_cip: z.string().nullable(),
  especialidad_id: z.string().nullable(),
  especialidad_nombre: z.string().nullable(),
  tipo: z.string().nullable(),
});

const contactoListItemSchema = z.object({
  id: z.string(),
  nombres: z.string().nullable(),
  apellidos: z.string().nullable(),
  dni: z.string().nullable(),
  cargo: z.string().nullable(),
  telefono: z.string().nullable(),
  celular: z.string().nullable(),
  email: z.string().nullable(),
  direccion: z.string().nullable(),
  principal: z.boolean(),
  descripcion: z.string().nullable(),
});

const tarifaRevisionListItemSchema = z.object({
  id: z.string(),
  costo_por_m2: z.number().nullable(),
  area_m2: z.number().nullable(),
  derecho_minimo: z.number().nullable(),
  derecho_maximo: z.number().nullable(),
  porcentaje_minimo_uit: z.number().nullable(),
  porcentaje_liquidacion: z.number().nullable(),
  costo_por_visita: z.number().nullable(),
  visitas_minimas: z.number().nullable(),
  categoria: z.string().nullable(),
});

const especialidadRevisionListItemSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});

const revisionListItemSchema = z.object({
  id: z.string(),
  especialidades: z.array(especialidadRevisionListItemSchema),
  tarifa: tarifaRevisionListItemSchema,
});

/** Item de lista */
const liquidacionMecanicaSuelosListItemSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  estado: z.string(),
  tipo_liquidacion: z.string(),
  numero_revision: z.number(),
  fecha_registro: z.string(),
  proyecto: proyectoListItemSchema,
  entidad: entidadListItemSchema,
  municipalidad: municipalidadListItemSchema,
  valores: valoresM2ListItemSchema,
  proyectistas: z.array(proyectistaListItemSchema),
  delegados: z.array(delegadoListItemSchema),
  contactos: z.array(contactoListItemSchema),
  revisiones: z.array(revisionListItemSchema),
});

/** Payload para respuesta de lista */
const liquidacionesMecanicaSuelosPayloadSchema = z.object({
  items: z.array(liquidacionMecanicaSuelosListItemSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
  total_pages: z.number(),
});

/** Wrapper para respuesta de lista */
export const liquidacionesMecanicaSuelosResponseSchema = apiResponseSchema(
  liquidacionesMecanicaSuelosPayloadSchema,
);

/** Flat list item type matching backend */
export type LiquidacionMecanicaSuelosListItem = z.infer<typeof liquidacionMecanicaSuelosListItemSchema>;

/** Wrapper para respuesta de detalle (single item) */
export const liquidacionMecanicaSuelosDetailResponseSchema = apiResponseSchema(
  liquidacionMecanicaSuelosListItemSchema,
);

// ── Crear Liquidación Response Schema ────────────────────────────────────────

/** Payload para respuesta de creación — flat list item structure */
const crearMecanicaSuelosPayloadSchema = liquidacionMecanicaSuelosListItemSchema;

/** Wrapper para respuesta de creación */
export const crearMecanicaSuelosResponseSchema =
  apiResponseSchema(crearMecanicaSuelosPayloadSchema);

// ── Form Step Schemas ──────────────────────────────────────────────────────────

/**
 * Schema para el step de Mecánica de Suelos (área y municipalidad).
 */
export const stepMecanicaSuelosSchema = z.object({
  municipalidad_id: z.string().uuid("Debe seleccionar una municipalidad"),
  area_solicitada: z
    .number()
    .positive("El área debe ser positiva"),
  expediente: z.string().optional(),
  observacion: z.string().optional(),
});

export type StepMecanicaSuelosData = z.infer<typeof stepMecanicaSuelosSchema>;

// ── Tarifas Vigentes Schemas ──────────────────────────────────────────────────

/** Tarifa vigente en respuesta del endpoint */
const tarifaVigenteMecanicaSuelosSchema = z.object({
  tarifa_id: z.string(),
  costo_por_m2: z.number(),
  area_m2: z.number(),
  derecho_minimo: z.number(),
  derecho_maximo: z.number().nullable(),
  habilitada: z.boolean(),
});

/** Wrapper para respuesta de tarifas vigentes */
export const tarifasVigentesMecanicaSuelosResponseSchema = apiResponseSchema(
  z.object({
    tarifas: z.array(tarifaVigenteMecanicaSuelosSchema),
  }),
);
