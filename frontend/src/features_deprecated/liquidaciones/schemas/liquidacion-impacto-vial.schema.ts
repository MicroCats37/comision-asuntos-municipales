/**
 * Zod schemas para Impacto Vial.
 * Endpoint base: /liquidaciones/impacto-vial
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";
import { contactoInlineSchema, proyectistaInlineSchema } from "./liquidacion-edificaciones-form.schema";

// ── Inner Schemas (data fields only) ──────────────────────────────────────────

/** Entidad inline para creación de proyecto inline */
const entidadInlineImpactoVialSchema = z.object({
  tipo_documento: z.enum(["RUC", "DNI"], {
    message: "Tipo de documento es requerido",
  }),
  numero_documento: z.string().min(1, "Número de documento es requerido"),
  razon_social: z.string().min(1, "Razón social o nombre completo es requerido"),
});

/** Proyecto inline para creación en línea */
export const proyectoInlineImpactoVialSchema = z.object({
  denominacion: z.string().min(1, "Denominación es requerida"),
  direccion: z.string().optional(),
  distrito_id: z.string().uuid("Distrito es requerido").optional(),
  nombre_propietario: z.string().min(1, "Nombre del propietario es requerido"),
  entidad: entidadInlineImpactoVialSchema,
});

/** XOR: proyecto_public_id O proyecto_inline, nunca ambos ni ninguno */
export const proyectoXorImpactoVialSchema = z
  .object({
    proyecto_public_id: z.string().optional(),
    proyecto_inline: proyectoInlineImpactoVialSchema.optional(),
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
 * Schema para primera revisión de Impacto Vial.
 */
export const primeraRevisionImpactoVialSchema = z.object({
  // XOR: uno de los dos es requerido
  proyecto_public_id: z.string().min(1, "Proyecto es requerido").optional(),
  proyecto_inline: proyectoInlineImpactoVialSchema.optional(),
  municipalidad_id: z.string().uuid("Municipalidad es requerida"),
  valor_proyecto: z.number().positive("El valor del proyecto debe ser positivo"),
  expediente: z.string().optional(),
  observacion: z.string().optional(),
  tarifas_ids: z.array(z.string().uuid()).min(1, "Debe seleccionar al menos una tarifa"),
  proyectistas: z.array(proyectistaInlineSchema).default([]),
  contactos: z.array(contactoInlineSchema).default([]),
});

export type PrimeraRevisionImpactoVialData = z.infer<typeof primeraRevisionImpactoVialSchema>;

// ── Cotizar Schemas ────────────────────────────────────────────────────────────

/** Payload para cotizar primera revisión — municipalidad NO requerida para cotizar; solo para creación final */
export const cotizarImpactoVialPayloadSchema = z.object({
  valor_proyecto: z.number().positive("El valor del proyecto debe ser positivo"),
  tarifas_ids: z.array(z.string().uuid()).min(1, "Debe seleccionar al menos una tarifa"),
});

/** Request para cotizar primera revisión */
export const cotizarImpactoVialRequestSchema = z.object({
  liquidacion: cotizarImpactoVialPayloadSchema,
});

// ── Cotizar Response Schemas ──────────────────────────────────────────────────

/** Totales en respuesta de cotización */
const cotizacionImpactoVialTotalesSchema = z.object({
  subtotal: z.number(),
  igv: z.number(),
  total: z.number(),
  liquidacion_total: z.number(),
  total_a_pagar: z.number(),
});

/** Metadata en respuesta de cotización (porcentaje-based — Edificaciones style) */
const cotizacionImpactoVialMetadataSchema = z.object({
  igv_valor: z.number(),
  uit_valor: z.number(),
  cobra: z.boolean(),
  valor_base_calculo: z.number(),
});

/** Tarifa en respuesta de cotización (porcentaje-based) */
const cotizacionImpactoVialTarifaSchema = z.object({
  id: z.string(),
  derecho_minimo: z.number(),
  derecho_maximo: z.number().nullable(),
  porcentaje_minimo_uit: z.number(),
  porcentaje_liquidacion: z.number(),
});

/** Revisión en respuesta de cotización (porcentaje-based — matches CotizacionRevision) */
const cotizacionImpactoVialRevisionSchema = z.object({
  id: z.string(),
  especialidades: z.array(
    z.object({
      id: z.string(),
      nombre: z.string(),
    }),
  ),
  tarifa: cotizacionImpactoVialTarifaSchema,
  monto_base: z.number(),
  cobra: z.boolean(),
});

/** Payload de respuesta de cotización (porcentaje-based — Edificaciones style) */
const cotizacionImpactoVialPayloadSchema = z.object({
  numero_revision: z.number(),
  revisiones: z.array(cotizacionImpactoVialRevisionSchema),
  totales: cotizacionImpactoVialTotalesSchema,
  _metadata: cotizacionImpactoVialMetadataSchema,
});

/** Wrapper para respuesta de cotización */
export const cotizacionImpactoVialResponseSchema =
  apiResponseSchema(cotizacionImpactoVialPayloadSchema);

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
const liquidacionImpactoVialListItemSchema = z.object({
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
const liquidacionesImpactoVialPayloadSchema = z.object({
  items: z.array(liquidacionImpactoVialListItemSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
  total_pages: z.number(),
});

/** Wrapper para respuesta de lista */
export const liquidacionesImpactoVialResponseSchema = apiResponseSchema(
  liquidacionesImpactoVialPayloadSchema,
);

/** Flat list item type matching backend */
export type LiquidacionImpactoVialListItem = z.infer<typeof liquidacionImpactoVialListItemSchema>;

/** Wrapper para respuesta de detalle (single item) */
export const liquidacionImpactoVialDetailResponseSchema = apiResponseSchema(
  liquidacionImpactoVialListItemSchema,
);

// ── Crear Liquidación Response Schema ────────────────────────────────────────

/** Payload para respuesta de creación — flat list item structure */
const crearImpactoVialPayloadSchema = liquidacionImpactoVialListItemSchema;

/** Wrapper para respuesta de creación */
export const crearImpactoVialResponseSchema =
  apiResponseSchema(crearImpactoVialPayloadSchema);

// ── Form Step Schemas ──────────────────────────────────────────────────────────

/**
 * Schema para el step de Impacto Vial (valor proyecto y municipalidad).
 */
export const stepImpactoVialSchema = z.object({
  municipalidad_id: z.string().uuid("Debe seleccionar una municipalidad"),
  valor_proyecto: z
    .number()
    .positive("El valor del proyecto debe ser positivo"),
  expediente: z.string().optional(),
  observacion: z.string().optional(),
});

export type StepImpactoVialData = z.infer<typeof stepImpactoVialSchema>;

// ── Tarifas Vigentes Schemas ──────────────────────────────────────────────────

/** Tarifa vigente en respuesta del endpoint (porcentaje-based) */
const tarifaVigenteImpactoVialSchema = z.object({
  tarifa_id: z.string(),
  porcentaje_liquidacion: z.number(),
  derecho_minimo: z.number(),
  derecho_maximo: z.number().nullable(),
  porcentaje_minimo_uit: z.number(),
  habilitada: z.boolean(),
});

/** Wrapper para respuesta de tarifas vigentes */
export const tarifasVigentesImpactoVialResponseSchema = apiResponseSchema(
  z.object({
    tarifas: z.array(tarifaVigenteImpactoVialSchema),
  }),
);
