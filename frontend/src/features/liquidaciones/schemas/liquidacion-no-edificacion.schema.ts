/**
 * Zod schemas para liquidaciones no edificación.
 * Incluye: Habilitación Urbana, Mecánica de Suelos, Impacto Vial, Taludes, Inspección de Obra.
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";
import { contactoInlineSchema } from "./liquidacion-edificaciones-form.schema";

// ── Kind Constants ─────────────────────────────────────────────────────────────

/** Kinds M2: todos excepto inspección de obra */
export const liquidacionM2KindsSchema = z.enum([
  "habilitacion-urbana",
  "mecanica-suelos",
  "impacto-vial",
  "taludes",
]);

/** Todos los kinds de no edificación */
export const liquidacionKindsSchema = z.enum([
  "habilitacion-urbana",
  "mecanica-suelos",
  "impacto-vial",
  "taludes",
  "inspeccion-obra",
]);

export type LiquidacionKinds = z.infer<typeof liquidacionKindsSchema>;
export type LiquidacionM2Kinds = z.infer<typeof liquidacionM2KindsSchema>;

// ── Inner Schemas (data fields only) ──────────────────────────────────────────

/** Entidad inline para creación de proyecto inline */
const entidadInlineNoEdificacionSchema = z.object({
  tipo_documento: z.enum(["RUC", "DNI"], {
    message: "Tipo de documento es requerido",
  }),
  numero_documento: z.string().min(1, "Número de documento es requerido"),
  razon_social: z.string().min(1, "Razón social o nombre completo es requerido"),
});

/** Proyecto inline para creación en línea (dentro de primera revisión)
 * Coincide con ProyectoInlineData del backend */
export const proyectoInlineNoEdificacionSchema = z.object({
  denominacion: z.string().min(1, "Denominación es requerida"),
  direccion: z.string().optional(),
  distrito_id: z.string().uuid("Distrito es requerido").optional(),
  nombre_propietario: z.string().min(1, "Nombre del propietario es requerido"),
  entidad: entidadInlineNoEdificacionSchema,
});

/** XOR: proyecto_public_id O proyecto_inline, nunca ambos ni ninguno */
export const proyectoXorNoEdificacionSchema = z
  .object({
    proyecto_public_id: z.string().optional(),
    proyecto_inline: proyectoInlineNoEdificacionSchema.optional(),
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

// ── M2 Schema (HU, MS, IV, Taludes) ───────────────────────────────────────────

/**
 * Schema para M2 primera revisión (Habilitación Urbana, Mecánica de Suelos,
 * Impacto Vial, Taludes).
 */
export const primeraRevisionM2Schema = z.object({
  // XOR: uno de los dos es requerido
  proyecto_public_id: z.string().min(1, "Proyecto es requerido").optional(),
  proyecto_inline: proyectoInlineNoEdificacionSchema.optional(),
  municipalidad_id: z.string().uuid("Municipalidad es requerida"),
  area_solicitada: z.number().positive("El área debe ser positiva"),
  expediente: z.string().optional(),
  observacion: z.string().optional(),
  tarifas_ids: z.array(z.string().uuid()).min(1, "Debe seleccionar al menos una tarifa"),
  contactos: z.array(contactoInlineSchema).default([]),
});

export type PrimeraRevisionM2Schema = z.infer<typeof primeraRevisionM2Schema>;

// ── Inspección de Obra Schema ─────────────────────────────────────────────────

/**
 * Categorías disponibles para inspección de obra.
 */
export const categoriaIOSchema = z.enum(["C1", "C2", "C3", "C4"]);

/**
 * Schema para Inspección de Obra primera revisión.
 */
export const primeraRevisionInspeccionObraSchema = z.object({
  // XOR: uno de los dos es requerido
  proyecto_public_id: z.string().min(1, "Proyecto es requerido").optional(),
  proyecto_inline: proyectoInlineNoEdificacionSchema.optional(),
  municipalidad_id: z.string().uuid("Municipalidad es requerida"),
  cantidad_visitas: z
    .number()
    .int("Cantidad de visitas debe ser un número entero")
    .positive("Cantidad de visitas debe ser al menos 1"),
  categoria: categoriaIOSchema,
  expediente: z.string().optional(),
  observacion: z.string().optional(),
  tarifas_ids: z.array(z.string().uuid()).min(1, "Debe seleccionar al menos una tarifa"),
  contactos: z.array(contactoInlineSchema).default([]),
});

export type PrimeraRevisionInspeccionObraSchema = z.infer<
  typeof primeraRevisionInspeccionObraSchema
>;

// ── Cotizar Schemas ────────────────────────────────────────────────────────────

/** Payload para cotizar primera revisión M2 */
export const cotizarM2PrimeraRevisionPayloadSchema = z.object({
  tipo_liquidacion: liquidacionM2KindsSchema,
  area_solicitada: z.number().positive("El área debe ser positiva"),
  municipalidad_id: z.string().uuid("Municipalidad es requerida"),
  tarifas_ids: z.array(z.string().uuid()).min(1, "Debe seleccionar al menos una tarifa"),
});

/** Request para cotizar M2 primera revisión */
export const cotizarM2PrimeraRevisionRequestSchema = z.object({
  liquidacion: cotizarM2PrimeraRevisionPayloadSchema,
});

/** Payload para cotizar inspección de obra primera revisión */
export const cotizarInspeccionObraPrimeraRevisionPayloadSchema = z.object({
  cantidad_visitas: z
    .number()
    .int("Cantidad de visitas debe ser un número entero")
    .positive("Cantidad de visitas debe ser al menos 1"),
  categoria: categoriaIOSchema,
  municipalidad_id: z.string().uuid("Municipalidad es requerida"),
  tarifas_ids: z.array(z.string().uuid()).min(1, "Debe seleccionar al menos una tarifa"),
});

/** Request para cotizar inspección de obra primera revisión */
export const cotizarInspeccionObraPrimeraRevisionRequestSchema = z.object({
  liquidacion: cotizarInspeccionObraPrimeraRevisionPayloadSchema,
});

// ── Cotizar Response Schemas ────────────────────────────────────────────────────

/** Totales en respuesta de cotización (both M2 and IO) */
const cotizacionTotalesNoEdificacionSchema = z.object({
  subtotal: z.number(),
  igv: z.number(),
  total: z.number(),
  liquidacion_total: z.number(),
  total_a_pagar: z.number(),
});

/** Metadata en respuesta de cotización M2 */
const cotizacionM2MetadataSchema = z.object({
  igv_valor: z.number(),
  uit_valor: z.number(),
  area_solicitada: z.number().optional(),
});

/** Tarifa M2 en respuesta de cotización */
const cotizacionM2TarifaSchema = z.object({
  id: z.string(),
  costo_por_m2: z.number(),
  area_minima: z.number(),
  derecho_minimo: z.number(),
  derecho_maximo: z.number().nullable(),
});

/** Cálculo M2 en respuesta de cotización */
const cotizacionM2CalculoSchema = z.object({
  area_solicitada: z.number(),
  area_base_calculo: z.number(),
  derecho: z.number(),
  tarifa: cotizacionM2TarifaSchema,
});

/** Payload de respuesta de cotización M2 (HU, MS, IV, Taludes) */
const cotizacionM2PayloadSchema = z.object({
  numero_revision: z.number(),
  calculo_m2: cotizacionM2CalculoSchema,
  totales: cotizacionTotalesNoEdificacionSchema,
  _metadata: cotizacionM2MetadataSchema,
});

/** Wrapper para respuesta de cotización M2 */
export const cotizacionM2ResponseSchema =
  apiResponseSchema(cotizacionM2PayloadSchema);

/** Metadata en respuesta de cotización IO */
const cotizacionIOMetadataSchema = z.object({
  igv_valor: z.number(),
  uit_valor: z.number(),
  cantidad_visitas: z.number().optional(),
});

/** Tarifa IO en respuesta de cotización */
const cotizacionIOTarifaSchema = z.object({
  id: z.string(),
  costo_por_visita: z.number(),
  visitas_minimas: z.number(),
});

/** Cálculo IO (visitas) en respuesta de cotización */
const cotizacionIOCalculoSchema = z.object({
  cantidad_visitas: z.number(),
  visitas_base_calculo: z.number(),
  derecho: z.number(),
  categoria: z.string(),
  tarifa: cotizacionIOTarifaSchema,
});

/** Payload de respuesta de cotización Inspección de Obra */
const cotizacionIOPayloadSchema = z.object({
  numero_revision: z.number(),
  calculo_visitas: cotizacionIOCalculoSchema,
  totales: cotizacionTotalesNoEdificacionSchema,
  _metadata: cotizacionIOMetadataSchema,
});

/** Wrapper para respuesta de cotización Inspección de Obra */
export const cotizacionIOResponseSchema =
  apiResponseSchema(cotizacionIOPayloadSchema);

// ── Crear Liquidación Response Schema ─────────────────────────────────────────

/** Payload para respuesta de creación de liquidación no-edificación */
const crearLiquidacionNoEdificacionPayloadSchema = z.object({
  liquidacion: z.object({
    id: z.string(),
    public_id: z.string(),
    estado: z.string(),
    fecha_creacion: z.string(),
    expediente: z.string().nullable(),
    observacion: z.string().nullable(),
  }),
  totales: z.object({
    subtotal: z.number(),
    igv: z.number(),
    total: z.number(),
    liquidacion_total: z.number(),
    total_a_pagar: z.number(),
  }),
});

/** Wrapper para respuesta de creación de liquidación no-edificación */
export const crearLiquidacionNoEdificacionResponseSchema =
  apiResponseSchema(crearLiquidacionNoEdificacionPayloadSchema);

// ── List Response Schemas ─────────────────────────────────────────────────────

/** Item de lista para liquidación no-edificación */
const liquidacionNoEdificacionListItemSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  estado: z.string(),
  fecha_registro: z.string(),
  expediente: z.string().nullable(),
  observacion: z.string().nullable(),
  municipalidad_id: z.string().nullable(),
  municipalidad_nombre: z.string().nullable(),
  /** Área para M2, cantidad_visitas para IO; null para edificaciones */
  valor_caracteristico: z.number().nullable(),
  /** Tipo específico: habilitacion-urbana, inspeccion-obra, etc. (slug) */
  tipo_liquidacion: liquidacionKindsSchema,
  proyecto_public_id: z.string().nullable(),
  proyecto_denominacion: z.string().nullable(),
});

/** Totales para lista de liquidación no-edificación */
const liquidacionNoEdificacionTotalesListSchema = z.object({
  subtotal: z.number(),
  igv: z.number(),
  total: z.number(),
  liquidacion_total: z.number(),
  total_a_pagar: z.number(),
});

/** Payload para respuesta de lista de liquidaciones no-edificación */
const liquidacionesNoEdificacionPayloadSchema = z.object({
  items: z.array(
    z.object({
      ...liquidacionNoEdificacionListItemSchema.shape,
      totales: liquidacionNoEdificacionTotalesListSchema.nullable(),
    }),
  ),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
  total_pages: z.number(),
});

/** Wrapper para respuesta de lista de liquidaciones no-edificación */
export const liquidacionesNoEdificacionResponseSchema = apiResponseSchema(
  liquidacionesNoEdificacionPayloadSchema,
);

// ── Form Step Schemas ──────────────────────────────────────────────────────────

/**
 * Schema para el step de proyecto (Step 1).
 * No se necesita validación especial — proyecto_public_id es un hidden field.
 */

/**
 * Schema para el step M2 (Step 2) — area y municipalidad.
 */
export const stepM2Schema = z.object({
  municipalidad_id: z.string().uuid("Debe seleccionar una municipalidad"),
  area_solicitada: z
    .number()
    .positive("El área debe ser positiva"),
  expediente: z.string().optional(),
  observacion: z.string().optional(),
});

export type StepM2Data = z.infer<typeof stepM2Schema>;

/**
 * Schema para el step Inspección de Obra (Step 2) — visitas y categoría.
 */
export const stepInspeccionObraSchema = z.object({
  municipalidad_id: z.string().uuid("Debe seleccionar una municipalidad"),
  cantidad_visitas: z
    .number()
    .int("Cantidad de visitas debe ser un número entero")
    .positive("Cantidad de visitas debe ser al menos 1"),
  categoria: categoriaIOSchema,
  expediente: z.string().optional(),
  observacion: z.string().optional(),
});

export type StepInspeccionObraData = z.infer<typeof stepInspeccionObraSchema>;

// ── Tarifas Vigentes Schemas ────────────────────────────────────────────────────

/** Tarifa M2 vigente en respuesta del endpoint */
const tarifaVigenteM2Schema = z.object({
  tarifa_id: z.string(),
  detalle_id: z.string(),
  costo_por_m2: z.number(),
  area_minima: z.number(),
  derecho_minimo: z.number(),
  derecho_maximo: z.number().nullable(),
  habilitada: z.boolean(),
});

/** Wrapper para respuesta de tarifas vigentes M2 */
export const tarifasVigentesM2ResponseSchema = apiResponseSchema(
  z.object({
    tarifas: z.array(tarifaVigenteM2Schema),
  }),
);

/** Tarifa de visita vigente en respuesta del endpoint */
const tarifaVigenteVisitaSchema = z.object({
  tarifa_id: z.string(),
  detalle_id: z.string(),
  costo_por_visita: z.number(),
  visitas_minimas: z.number(),
  categoria: z.string(),
  habilitada: z.boolean(),
});

/** Wrapper para respuesta de tarifas vigentes de inspección de obra */
export const tarifasVigentesVisitasResponseSchema = apiResponseSchema(
  z.object({
    tarifas: z.array(tarifaVigenteVisitaSchema),
  }),
);
