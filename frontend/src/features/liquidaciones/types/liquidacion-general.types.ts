/**
 * Shared Zod schemas and TypeScript types for Liquidaciones.
 * Follows the 3-wrapper pattern from backend:
 * liquidacion_general + liquidacion_especifica + liquidacion_tipo
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

// ── Common Enums ───────────────────────────────────────────────────────────────

export const tipoLiquidacionSchema = z.enum([
  "EDIFICACION",
  "HABILITACION_URBANA",
  "MECANICA_SUELOS",
  "IMPACTO_VIAL",
  "TALUDES",
  "INSPECCION_OBRA",
]);
export type TipoLiquidacion = z.infer<typeof tipoLiquidacionSchema>;

export const estadoLiquidacionSchema = z.enum([
  "BORRADOR",
  "PENDIENTE",
  "APROBADO",
  "RECHAZADO",
  "CANCELADO",
]);
export type EstadoLiquidacion = z.infer<typeof estadoLiquidacionSchema>;

// ── 3-Wrapper Base Types ──────────────────────────────────────────────────────

/** Wrapper for liquidacion_general — matches LiquidacionGeneralOutput from backend */
export const liquidacionGeneralWrapperSchema = z.object({
  id: z.string(),
  municipalidad_id: z.string(),
  usuario_creador: z.object({ id: z.string() }),
  fecha_registro: z.string(),
  expediente: z.string().nullable(),
  observacion: z.string().nullable(),
  numero_revision: z.number(),
  sub_total: z.number(),
  total: z.number(),
  igv_id: z.string().nullable(),
  uit_id: z.string().nullable(),
  igv_snapshot: z.number().nullable(),
  uit_snapshot: z.number().nullable(),
  estado: estadoLiquidacionSchema,
  tipo_liquidacion: tipoLiquidacionSchema,
  retencion: z.boolean().default(false),
  proyecto: z.object({
    id: z.string(),
    public_id: z.string(),
    denominacion: z.string(),
    nombre_propietario: z.string(),
    direccion: z.string().nullable(),
    distrito_id: z.string().nullable(),
    entidad: z
      .object({
        tipo_documento: z.string().nullable(),
        numero_documento: z.string().nullable(),
        razon_social: z.string().nullable(),
      })
      .nullable(),
  }),
});
export type LiquidacionGeneralWrapper = z.infer<typeof liquidacionGeneralWrapperSchema>;

/** Wrapper for liquidacion_especifica — matches LiquidacionTipoOutput from backend */
export const liquidacionEspecificaWrapperSchema = z.object({
  id: z.string(),
  numero: z.number(),
});
export type LiquidacionEspecificaWrapper = z.infer<typeof liquidacionEspecificaWrapperSchema>;

// ── List Item Types ────────────────────────────────────────────────────────────

/**
 * Generic list item — T is the domain-specific liquidacion_tipo.
 * Matches the backend's 3-wrapper output pattern.
 */
export interface LiquidacionListItem<T> {
  liquidacion_general: LiquidacionGeneralWrapper;
  liquidacion_especifica: LiquidacionEspecificaWrapper;
  liquidacion_tipo: T;
}

/** Base list item for liquidacion cards */
export type LiquidacionCardBase = LiquidacionGeneralWrapper;

// ── Variables Financieras ─────────────────────────────────────────────────────

export const variablesFinancierasSchema = z.object({
  igv_valor: z.number(),
  igv_porcentaje: z.number(),
  igv_periodo_inicio: z.string().nullable(),
  uit_valor: z.number(),
  uit_anio: z.number().nullable(),
  uit_periodo_inicio: z.string().nullable(),
});
export type VariablesFinancieras = z.infer<typeof variablesFinancierasSchema>;

// ── Nested Common Schemas ─────────────────────────────────────────────────────

export const entidadInlineSchema = z.object({
  id: z.string().nullable(),
  tipo: z.string().nullable(),
  nombre: z.string().nullable(),
  ruc: z.string().nullable(),
});

export const proyectoInlineSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  nombre: z.string(),
  direccion: z.string().nullable(),
  valor_proyecto: z.number(),
  entidad: entidadInlineSchema.nullable(),
});

export const municipalidadInlineSchema = z.object({
  id: z.string(),
  nombre: z.string(),
  codigo: z.string().nullable(),
  provincia: z.object({ id: z.string(), nombre: z.string() }).nullable(),
  distrito: z.object({ id: z.string(), nombre: z.string() }).nullable(),
});

export const especialidadBasicaSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});

export const tarifaBasicaSchema = z.object({
  id: z.string(),
  derecho_minimo: z.number().nullable(),
  derecho_maximo: z.number().nullable(),
  porcentaje_minimo_uit: z.number(),
  porcentaje_liquidacion: z.number(),
  // Extended fields from domain-specific tarifas (IO, HU, MS, Edificaciones, IV, Taludes)
  valor_declarado: z.number().nullable().optional(),
  area_m2: z.number().nullable().optional(),
  costo_por_m2: z.number().nullable().optional(),
  categoria: z.string().nullable().optional(),
  cantidad_visitas: z.number().nullable().optional(),
  costo_por_visita: z.number().nullable().optional(),
  visitas_minimas: z.number().nullable().optional(),
  detalles: z.array(z.object({
    id: z.string(),
    tarifa_aplicada_id: z.string(),
    especialidad_id: z.string(),
    porcentaje_aplicado: z.number(),
    subtotal: z.number(),
    igv: z.number(),
    uit: z.number(),
    total: z.number(),
  })).nullable().optional(),
});

export const revisionBasicaSchema = z.object({
  id: z.string(),
  especialidades: z.array(especialidadBasicaSchema),
  tarifa: tarifaBasicaSchema.nullable(),
});

export const valoresFinancierosSchema = z.object({
  subtotal: z.number(),
  igv: z.number(),
  total: z.number(),
  total_a_pagar: z.number(),
});

// ── Generic Paginated Response ────────────────────────────────────────────────

export const paginatedLiquidacionListPayloadSchema = <T extends z.ZodTypeAny>(itemSchema: T) =>
  z.object({
    items: z.array(itemSchema),
    total: z.number(),
    page: z.number(),
    page_size: z.number(),
    total_pages: z.number(),
  });

export const paginatedLiquidacionListResponseSchema = <T extends z.ZodTypeAny>(itemSchema: T) =>
  apiResponseSchema(paginatedLiquidacionListPayloadSchema(itemSchema));

// ── LiquidacionGeneralOut (for detail views) ──────────────────────────────────

const proyectoGeneralSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  nombre: z.string(),
  direccion: z.string().nullable(),
});

const entidadGeneralSchema = z.object({
  id: z.string().nullable(),
  tipo: z.string().nullable(),
  nombre: z.string().nullable(),
  ruc: z.string().nullable(),
});

export const liquidacionGeneralOutSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  estado: z.string(),
  tipo_liquidacion: z.string(),
  numero_revision: z.number(),
  fecha_registro: z.string(),
  expediente: z.string().nullable(),
  observacion: z.string().nullable(),
  municipalidad_nombre: z.string().nullable(),
  proyecto: proyectoGeneralSchema.nullable(),
  entidad: entidadGeneralSchema.nullable(),
  subtotal: z.number(),
  igv: z.number(),
  total: z.number(),
  total_a_pagar: z.number(),
});

export type LiquidacionGeneralOut = z.infer<typeof liquidacionGeneralOutSchema>;
