/**
 * Zod schemas para liquidaciones GENERALES.
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";

const entidadListItemSchema = z.object({
  id: z.string().nullable(),
  tipo: z.string().nullable(),
  nombre: z.string().nullable(),
  ruc: z.string().nullable(),
});

const proyectoSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  nombre: z.string(),
  direccion: z.string().nullable(),
  valor_proyecto: z.number(),
  entidad: entidadListItemSchema.nullable(),
});

const municipalidadSchema = z.object({
  id: z.string(),
  nombre: z.string(),
  codigo: z.string().nullable(),
  provincia: z.null(),
  distrito: z.null(),
});

const valoresSchema = z.object({
  subtotal: z.number(),
  igv: z.number(),
  total: z.number(),
  total_a_pagar: z.number(),
});

const proyectistaSchema = z.object({
  id: z.string(),
  perfil_ingeniero_id: z.string().nullable(),
  perfil_ingeniero_nombres: z.string().nullable(),
  perfil_ingeniero_apellidos: z.string().nullable(),
  perfil_ingeniero_cip: z.string().nullable(),
  especialidad_id: z.string().nullable(),
  especialidad_nombre: z.string().nullable(),
  descripcion: z.string().nullable(),
});

const delegadoSchema = z.object({
  id: z.string(),
  perfil_ingeniero_id: z.string().nullable(),
  perfil_ingeniero_nombres: z.string().nullable(),
  perfil_ingeniero_apellidos: z.string().nullable(),
  perfil_ingeniero_cip: z.string().nullable(),
  especialidad_id: z.string().nullable(),
  especialidad_nombre: z.string().nullable(),
  tipo: z.string().nullable(),
});

const inspectorSchema = z.object({
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

const contactoSchema = z.object({
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

const tarifaRevisionSchema = z.object({
  id: z.string(),
});

const especialidadRevisionSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});

const revisionSchema = z.object({
  id: z.string(),
  especialidades: z.array(especialidadRevisionSchema),
  tarifa: tarifaRevisionSchema.nullable(),
});

/**
 * Variables financieras (IGV/UIT) usadas al crear la liquidacion.
 */
export const variablesFinancierasUsadasSchema = z.object({
  igv_valor: z.number(),
  igv_porcentaje: z.number(),
  igv_periodo_inicio: z.string().nullable(),
  uit_valor: z.number(),
  uit_anio: z.number().nullable(),
  uit_periodo_inicio: z.string().nullable(),
});

/**
 * Schema para item de lista paginada de liquidaciones GENERALES (Phase 5).
 * Coincide con LiquidacionGeneralListItemOut del backend.
 */
export const liquidacionGeneralListItemPayloadSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  estado: z.string(),
  tipo_liquidacion: z.string(),
  numero_revision: z.number(),
  fecha_registro: z.string(),
  tramite_accion: z.string().nullable(),
  tipo_tramite: z.string().nullable(),
  expediente: z.string().nullable(),
  observacion: z.string().nullable(),
  proyecto: proyectoSchema,
  entidad: entidadListItemSchema.nullable(),
  municipalidad: municipalidadSchema,
  valores: valoresSchema,
  proyectistas: z.array(proyectistaSchema),
  delegados: z.array(delegadoSchema),
  inspectores: z.array(inspectorSchema).default([]),
  contactos: z.array(contactoSchema),
  revisiones: z.array(revisionSchema),
  subtotal: z.number(),
  igv: z.number(),
  total: z.number(),
  total_a_pagar: z.number(),
  variables_financieras_usadas: variablesFinancierasUsadasSchema.nullable(),
});

/** Schema payload para lista paginada general */
export const paginatedLiquidacionGeneralListPayloadSchema = z.object({
  items: z.array(liquidacionGeneralListItemPayloadSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
  total_pages: z.number(),
});

/** Wrapper schema para lista paginada general (ApiResponse[PaginatedData[LiquidacionGeneralListItemOut]]) */
export const liquidacionGeneralListResponseSchema = apiResponseSchema(
  paginatedLiquidacionGeneralListPayloadSchema,
);

// ── Schemas para detalle general (LiquidacionGeneralOut) ──────────────────────

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

export const liquidacionGeneralDetailResponseSchema = apiResponseSchema(
  liquidacionGeneralOutSchema,
);
