/**
 * Zod schemas para Inspección de Obra.
 * Endpoint base: /liquidaciones/inspeccion-obra
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";
import { contactoInlineSchema, proyectistaInlineSchema } from "./liquidacion-edificaciones-form.schema";
import {
  liquidacionGeneralListItemPayloadSchema,
  paginatedLiquidacionGeneralListPayloadSchema,
} from "./liquidacion-general.schema";

// ── Inner Schemas (data fields only) ─────────────────────────────────────────

/** Entidad inline para creación de proyecto inline */
const entidadInlineIOSchema = z.object({
  tipo_documento: z.enum(["RUC", "DNI"], {
    message: "Tipo de documento es requerido",
  }),
  numero_documento: z.string().min(1, "Número de documento es requerido"),
  razon_social: z.string().min(1, "Razón social o nombre completo es requerido"),
});

/** Proyecto inline para creación en línea */
export const proyectoInlineIOSchema = z.object({
  denominacion: z.string().min(1, "Denominación es requerida"),
  direccion: z.string().optional(),
  distrito_id: z.string().uuid("Distrito es requerido").optional(),
  nombre_propietario: z.string().min(1, "Nombre del propietario es requerido"),
  entidad: entidadInlineIOSchema,
});

/** XOR: proyecto_public_id O proyecto_inline, nunca ambos ni ninguno */
export const proyectoXorIOSchema = z
  .object({
    proyecto_public_id: z.string().optional(),
    proyecto_inline: proyectoInlineIOSchema.optional(),
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

// ── Categorías Schema ─────────────────────────────────────────────────────────

/**
 * Categorías disponibles para inspección de obra.
 */
export const categoriaIOSchema = z.enum(["C1", "C2", "C3", "C4"]);

const cantidadVisitasSchema = z
  .union([z.number(), z.nan()])
  .refine((value) => Number.isFinite(value), {
    message: "Cantidad de visitas es requerida",
  })
  .pipe(
    z
      .number()
      .int("Cantidad de visitas debe ser un número entero")
      .min(1, "Cantidad de visitas debe ser al menos 1"),
  );

// ── Primera Revisión Schema ──────────────────────────────────────────────────

/**
 * Schema para primera revisión de Inspección de Obra basada en liquidación previa.
 *
 * Phase 1+: liquidacion_previa_id es requerido.
 * Los campos proyecto_public_id, proyecto_inline y municipalidad_id son opcionales
 * (deprecated) porque se ignoran en la creación — se derivan de la previa.
 */
export const primeraRevisionInspeccionObraSchema = z.object({
  // Phase 1+: opcional por ahora para compatibilidad con UI existente
  // Phase 5+ lo hará requerido cuando la UI envíe este campo
  liquidacion_previa_id: z.string().uuid("Liquidación previa es requerida").optional(),
  // DEPRECATED: se ignoran en la creación (se derivan de liquidacion_previa)
  proyecto_public_id: z.string().optional(),
  proyecto_inline: proyectoInlineIOSchema.optional(),
  municipalidad_id: z.string().uuid().optional(),
  cantidad_visitas: cantidadVisitasSchema,
  categoria: categoriaIOSchema,
  expediente: z.string().optional(),
  observacion: z.string().optional(),
  tarifas_ids: z.array(z.string().uuid()).min(1, "Debe seleccionar al menos una tarifa"),
  proyectistas: z.array(proyectistaInlineSchema).default([]),
  contactos: z.array(contactoInlineSchema).default([]),
});

/**
 * Schema para buscar liquidaciones previas de IO.
 * Endpoint: GET /liquidaciones/inspeccion-obra/buscar-previas
 * Usa liquidacionInspeccionObraListItemSchema para los items.
 */
export type BuscarLiquidacionesPreviasIOData = z.infer<typeof liquidacionInspeccionObraListItemSchema>;

export type PrimeraRevisionInspeccionObraData = z.infer<typeof primeraRevisionInspeccionObraSchema>;

// ── Cotizar Schemas ────────────────────────────────────────────────────────────

/** Payload para cotizar primera revisión */
export const cotizarInspeccionObraPayloadSchema = z.object({
  cantidad_visitas: cantidadVisitasSchema,
  categoria: categoriaIOSchema,
  // municipalidad_id NO es requerida para cotizar; solo para creación final
  tarifas_ids: z.array(z.string().uuid()).min(1, "Debe seleccionar al menos una tarifa"),
});

/** Request para cotizar primera revisión */
export const cotizarInspeccionObraRequestSchema = z.object({
  liquidacion: cotizarInspeccionObraPayloadSchema,
});

// ── Cotizar Response Schemas ──────────────────────────────────────────────────

/** Totales en respuesta de cotización */
const cotizacionIOTotalesSchema = z.object({
  subtotal: z.number(),
  igv: z.number(),
  total: z.number(),
  liquidacion_total: z.number(),
  total_a_pagar: z.number(),
});

/** Metadata en respuesta de cotización */
const cotizacionIOMetadataSchema = z.object({
  igv_valor: z.number(),
  uit_valor: z.number(),
  cantidad_visitas: z.number().optional(),
});

/** Tarifa en respuesta de cotización */
const cotizacionIOTarifaSchema = z.object({
  id: z.string(),
  costo_por_visita: z.number(),
  visitas_minimas: z.number(),
});

/** Cálculo en respuesta de cotización */
const cotizacionIOCalculoSchema = z.object({
  cantidad_visitas: z.number(),
  visitas_base_calculo: z.number(),
  derecho: z.number(),
  categoria: z.string(),
  tarifa: cotizacionIOTarifaSchema,
});

/** Payload de respuesta de cotización */
const cotizacionIOPayloadSchema = z.object({
  numero_revision: z.number(),
  calculo_visitas: cotizacionIOCalculoSchema,
  totales: cotizacionIOTotalesSchema,
  _metadata: cotizacionIOMetadataSchema,
});

/** Wrapper para respuesta de cotización */
export const cotizacionIOResponseSchema =
  apiResponseSchema(cotizacionIOPayloadSchema);

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

const valoresListItemSchema = z.object({
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

const inspectorListItemSchema = z.object({
  id: z.string(),
  perfil_ingeniero_id: z.string().nullable(),
  perfil_ingeniero_nombres: z.string().nullable(),
  perfil_ingeniero_apellidos: z.string().nullable(),
  perfil_ingeniero_cip: z.string().nullable(),
  especialidad_id: z.string().nullable(),
  especialidad_nombre: z.string().nullable(),
  tipo_liquidacion: z.string().nullable(),
  categoria: z.number().nullable(),
  numero_registro: z.string().nullable(),
  vigencia: z.string().nullable(),
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
  cantidad_visitas: z.number().nullable(),
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
const liquidacionInspeccionObraListItemSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  estado: z.string(),
  tipo_liquidacion: z.string(),
  numero_revision: z.number(),
  fecha_registro: z.string(),
  proyecto: proyectoListItemSchema,
  entidad: entidadListItemSchema,
  municipalidad: municipalidadListItemSchema,
  valores: valoresListItemSchema,
  proyectistas: z.array(proyectistaListItemSchema),
  delegados: z.array(delegadoListItemSchema),
  inspectores: z.array(inspectorListItemSchema).default([]),
  contactos: z.array(contactoListItemSchema),
  revisiones: z.array(revisionListItemSchema),
});

/** Payload para respuesta de lista */
const liquidacionesInspeccionObraPayloadSchema = z.object({
  items: z.array(liquidacionInspeccionObraListItemSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
  total_pages: z.number(),
});

/** Wrapper para respuesta de lista */
export const liquidacionesInspeccionObraResponseSchema = apiResponseSchema(
  liquidacionesInspeccionObraPayloadSchema,
);

/** Wrapper para respuesta de detalle (single item) */
export const liquidacionInspeccionObraDetailResponseSchema = apiResponseSchema(
  liquidacionInspeccionObraListItemSchema,
);

// ── Crear Liquidación Response Schema ────────────────────────────────────────

/** Payload para respuesta de creación — flat list item structure */
const crearInspeccionObraPayloadSchema = liquidacionInspeccionObraListItemSchema;

/** Wrapper para respuesta de creación */
export const crearInspeccionObraResponseSchema =
  apiResponseSchema(crearInspeccionObraPayloadSchema);

// ── Form Step Schemas ──────────────────────────────────────────────────────────

/**
 * Schema para el step de Inspección de Obra (visitas y categoría).
 */
export const stepInspeccionObraSchema = z.object({
  municipalidad_id: z.string().uuid("Debe seleccionar una municipalidad"),
  cantidad_visitas: cantidadVisitasSchema,
  categoria: categoriaIOSchema,
  expediente: z.string().optional(),
  observacion: z.string().optional(),
});

export type StepInspeccionObraData = z.infer<typeof stepInspeccionObraSchema>;

// ── Tarifas Vigentes Schemas ──────────────────────────────────────────────────

/** Tarifa vigente en respuesta del endpoint */
const tarifaVigenteInspeccionObraSchema = z.object({
  tarifa_id: z.string(),
  costo_por_visita: z.number(),
  visitas_minimas: z.number(),
  categoria: z.string(),
  habilitada: z.boolean(),
});

/** Wrapper para respuesta de tarifas vigentes */
export const tarifasVigentesInspeccionObraResponseSchema = apiResponseSchema(
  z.object({
    tarifas: z.array(tarifaVigenteInspeccionObraSchema),
  }),
);

// ── Buscar Previas Schemas ───────────────────────────────────────────────────

/**
 * Schema para búsqueda de liquidaciones previas de IO.
 * Ahora reutiliza el schema de lista general (LiquidacionGeneralListItemOut).
 * Endpoint: GET /liquidaciones/inspeccion-obra/buscar-previas
 */
export const buscarLiquidacionesPreviasIOResponseSchema = apiResponseSchema(
  paginatedLiquidacionGeneralListPayloadSchema,
);
