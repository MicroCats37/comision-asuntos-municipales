/**
 * Zod detail response schemas for liquidaciones.
 * Migrated from features_deprecated (exact shapes preserved).
 * Endpoints: GET /liquidaciones/{tipo}/{id}
 */
import { z } from "zod";
import { apiResponseSchema } from "@/types/api.types";
import {
  TipoTramiteEdificacionesSchema,
  TramiteAccionSchema,
} from "./tramite.schema";

// ── Shared List Item Sub-schemas (shape identical across deprecated types) ────

const detailProyectoListItemSchema = z.object({
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

const detailEntidadListItemSchema = z.object({
  id: z.string().nullable(),
  tipo: z.string().nullable(),
  nombre: z.string().nullable(),
  ruc: z.string().nullable(),
});

const detailMunicipalidadListItemSchema = z.object({
  id: z.string(),
  nombre: z.string(),
  codigo: z.string().nullable(),
  provincia: z.null(),
  distrito: z.null(),
});

const detailValoresListItemSchema = z.object({
  subtotal: z.number(),
  igv: z.number(),
  total: z.number(),
  total_a_pagar: z.number(),
});

const detailProyectistaListItemSchema = z.object({
  id: z.string(),
  perfil_ingeniero_id: z.string().nullable(),
  perfil_ingeniero_nombres: z.string().nullable(),
  perfil_ingeniero_apellidos: z.string().nullable(),
  perfil_ingeniero_cip: z.string().nullable(),
  especialidad_id: z.string().nullable(),
  especialidad_nombre: z.string().nullable(),
  descripcion: z.string().nullable(),
});

const detailDelegadoListItemSchema = z.object({
  id: z.string(),
  perfil_ingeniero_id: z.string().nullable(),
  perfil_ingeniero_nombres: z.string().nullable(),
  perfil_ingeniero_apellidos: z.string().nullable(),
  perfil_ingeniero_cip: z.string().nullable(),
  especialidad_id: z.string().nullable(),
  especialidad_nombre: z.string().nullable(),
  tipo: z.string().nullable(),
});

const detailContactoListItemSchema = z.object({
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

const detailInspectorListItemSchema = z.object({
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

const detailTarifaRevisionListItemSchema = z.object({
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

/** Tarifa de revisión para Inspección de Obra (incluye cantidad_visitas) */
const detailTarifaRevisionIOLListItemSchema = z.object({
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

const detailEspecialidadRevisionListItemSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});

const detailRevisionListItemSchema = z.object({
  id: z.string(),
  especialidades: z.array(detailEspecialidadRevisionListItemSchema),
  tarifa: detailTarifaRevisionListItemSchema,
});

const detailRevisionIOLListItemSchema = z.object({
  id: z.string(),
  especialidades: z.array(detailEspecialidadRevisionListItemSchema),
  tarifa: detailTarifaRevisionIOLListItemSchema,
});

/** Variables financieras (IGV/UIT) usadas al crear la liquidacion */
export const detailVariablesFinancierasUsadasSchema = z.object({
  igv_valor: z.number(),
  igv_porcentaje: z.number(),
  igv_periodo_inicio: z.string().nullable(),
  uit_valor: z.number(),
  uit_anio: z.number().nullable(),
  uit_periodo_inicio: z.string().nullable(),
});

// ── Taludes ────────────────────────────────────────────────────────────────────

/** Item de lista (detalle) — flat structure from backend */
const liquidacionTaludesDetailPayloadSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  estado: z.string(),
  tipo_liquidacion: z.string(),
  numero_revision: z.number(),
  fecha_registro: z.string(),
  proyecto: detailProyectoListItemSchema,
  entidad: detailEntidadListItemSchema,
  municipalidad: detailMunicipalidadListItemSchema,
  valores: detailValoresListItemSchema,
  proyectistas: z.array(detailProyectistaListItemSchema),
  delegados: z.array(detailDelegadoListItemSchema),
  contactos: z.array(detailContactoListItemSchema),
  revisiones: z.array(detailRevisionListItemSchema),
});

/** Wrapper para respuesta de detalle (single item) */
export const liquidacionTaludesDetailResponseSchema = apiResponseSchema(
  liquidacionTaludesDetailPayloadSchema,
);

// ── Mecánica de Suelos ────────────────────────────────────────────────────────

/** Item de lista (detalle) — flat structure from backend */
const liquidacionMecanicaSuelosDetailPayloadSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  estado: z.string(),
  tipo_liquidacion: z.string(),
  numero_revision: z.number(),
  fecha_registro: z.string(),
  proyecto: detailProyectoListItemSchema,
  entidad: detailEntidadListItemSchema,
  municipalidad: detailMunicipalidadListItemSchema,
  valores: detailValoresListItemSchema,
  proyectistas: z.array(detailProyectistaListItemSchema),
  delegados: z.array(detailDelegadoListItemSchema),
  contactos: z.array(detailContactoListItemSchema),
  revisiones: z.array(detailRevisionListItemSchema),
});

/** Wrapper para respuesta de detalle (single item) */
export const liquidacionMecanicaSuelosDetailResponseSchema = apiResponseSchema(
  liquidacionMecanicaSuelosDetailPayloadSchema,
);

// ── Inspección de Obra ─────────────────────────────────────────────────────────

/** Item de lista (detalle) — flat structure from backend */
const liquidacionInspeccionObraDetailPayloadSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  estado: z.string(),
  tipo_liquidacion: z.string(),
  numero_revision: z.number(),
  fecha_registro: z.string(),
  proyecto: detailProyectoListItemSchema,
  entidad: detailEntidadListItemSchema,
  municipalidad: detailMunicipalidadListItemSchema,
  valores: detailValoresListItemSchema,
  proyectistas: z.array(detailProyectistaListItemSchema),
  delegados: z.array(detailDelegadoListItemSchema),
  inspectores: z.array(detailInspectorListItemSchema).default([]),
  contactos: z.array(detailContactoListItemSchema),
  revisiones: z.array(detailRevisionIOLListItemSchema),
  variables_financieras_usadas:
    detailVariablesFinancierasUsadasSchema.nullable(),
});

/** Wrapper para respuesta de detalle (single item) */
export const liquidacionInspeccionObraDetailResponseSchema = apiResponseSchema(
  liquidacionInspeccionObraDetailPayloadSchema,
);

// ── Impacto Vial ───────────────────────────────────────────────────────────────

/** Item de lista (detalle) — flat structure from backend */
const liquidacionImpactoVialDetailPayloadSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  estado: z.string(),
  tipo_liquidacion: z.string(),
  numero_revision: z.number(),
  fecha_registro: z.string(),
  proyecto: detailProyectoListItemSchema,
  entidad: detailEntidadListItemSchema,
  municipalidad: detailMunicipalidadListItemSchema,
  valores: detailValoresListItemSchema,
  proyectistas: z.array(detailProyectistaListItemSchema),
  delegados: z.array(detailDelegadoListItemSchema),
  contactos: z.array(detailContactoListItemSchema),
  revisiones: z.array(detailRevisionListItemSchema),
});

/** Wrapper para respuesta de detalle (single item) */
export const liquidacionImpactoVialDetailResponseSchema = apiResponseSchema(
  liquidacionImpactoVialDetailPayloadSchema,
);

// ── Habilitación Urbana ────────────────────────────────────────────────────────

/** Item de lista (detalle) — flat structure from backend */
const liquidacionHabilitacionUrbanaDetailPayloadSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  estado: z.string(),
  tipo_liquidacion: z.string(),
  numero_revision: z.number(),
  fecha_registro: z.string(),
  proyecto: detailProyectoListItemSchema,
  entidad: detailEntidadListItemSchema,
  municipalidad: detailMunicipalidadListItemSchema,
  valores: detailValoresListItemSchema,
  proyectistas: z.array(detailProyectistaListItemSchema),
  delegados: z.array(detailDelegadoListItemSchema),
  contactos: z.array(detailContactoListItemSchema),
  revisiones: z.array(detailRevisionListItemSchema),
});

/** Wrapper para respuesta de detalle (single item) */
export const liquidacionHabilitacionUrbanaDetailResponseSchema =
  apiResponseSchema(liquidacionHabilitacionUrbanaDetailPayloadSchema);

// ── Edificaciones (LiquidacionEdificacionOut) ──────────────────────────────────

const detailEdificacionEspecialidadOutSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});

const detailEdificacionTarifaOutSchema = z.object({
  id: z.string(),
  derecho_minimo: z.number().nullable(),
  derecho_maximo: z.number().nullable(),
  porcentaje_minimo_uit: z.number().nullable(),
  porcentaje_liquidacion: z.number(),
});

const detailEdificacionRevisionOutSchema = z.object({
  id: z.string(),
  especialidades: z.array(detailEdificacionEspecialidadOutSchema),
  tarifa: detailEdificacionTarifaOutSchema,
});

const detailEdificacionEntidadOutSchema = z.object({
  id: z.string().nullable(),
  tipo: z.string().nullable(),
  nombre: z.string().nullable(),
  ruc: z.string().nullable(),
});

const detailEdificacionProyectoOutSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  nombre: z.string(),
  direccion: z.string().nullable(),
  valor_proyecto: z.union([z.number(), z.string()]),
  entidad: detailEdificacionEntidadOutSchema.nullable(),
});

const detailEdificacionProvinciaBasicOutSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});

const detailEdificacionDistritoBasicOutSchema = z.object({
  id: z.string(),
  nombre: z.string(),
  provincia: detailEdificacionProvinciaBasicOutSchema.nullable(),
});

const detailEdificacionMunicipalidadOutSchema = z.object({
  id: z.string(),
  nombre: z.string(),
  codigo: z.string().nullable(),
  provincia: detailEdificacionProvinciaBasicOutSchema.nullable(),
  distrito: detailEdificacionDistritoBasicOutSchema.nullable(),
});

const detailEdificacionValoresOutSchema = z.object({
  subtotal: z.union([z.number(), z.string()]),
  igv: z.union([z.number(), z.string()]),
  total: z.union([z.number(), z.string()]),
  total_a_pagar: z.union([z.number(), z.string()]),
});

const detailEdificacionProyectistaOutSchema = z.object({
  id: z.string(),
  perfil_ingeniero_id: z.string().nullable(),
  perfil_ingeniero_nombres: z.string().nullable(),
  perfil_ingeniero_apellidos: z.string().nullable(),
  perfil_ingeniero_cip: z.string().nullable(),
  especialidad_id: z.string().nullable(),
  especialidad_nombre: z.string().nullable(),
  descripcion: z.string().nullable(),
});

const detailEdificacionDelegadoOutSchema = z.object({
  id: z.string(),
  perfil_ingeniero_id: z.string().nullable(),
  perfil_ingeniero_nombres: z.string().nullable(),
  perfil_ingeniero_apellidos: z.string().nullable(),
  perfil_ingeniero_cip: z.string().nullable(),
  especialidad_id: z.string().nullable(),
  especialidad_nombre: z.string().nullable(),
  tipo: z.string().nullable(),
});

const detailEdificacionContactoOutSchema = z.object({
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

/**
 * Payload schema para respuesta de creación/detalle de LiquidacionEdificacionOut.
 * Estructura PLANA con objetos anidados que coincide con el backend.
 */
export const liquidacionEdificacionOutPayloadSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  estado: z.string(),
  tipo_liquidacion: z.string(),
  fecha_registro: z.string(),
  expediente: z.string().nullable(),
  observacion: z.string().nullable(),
  numero_revision: z.number(),
  tipo_tramite: TipoTramiteEdificacionesSchema,
  tramite_accion: TramiteAccionSchema,
  proyecto: detailEdificacionProyectoOutSchema,
  entidad: detailEdificacionEntidadOutSchema.nullable(),
  municipalidad: detailEdificacionMunicipalidadOutSchema,
  valores: detailEdificacionValoresOutSchema,
  proyectistas: z.array(detailEdificacionProyectistaOutSchema),
  delegados: z.array(detailEdificacionDelegadoOutSchema),
  contactos: z.array(detailEdificacionContactoOutSchema),
  revisiones: z.array(detailEdificacionRevisionOutSchema),
  subtotal: z.union([z.number(), z.string()]),
  igv: z.union([z.number(), z.string()]),
  total: z.union([z.number(), z.string()]),
  total_a_pagar: z.union([z.number(), z.string()]),
});

/** Wrapper schema para respuesta de creación/detalle (ApiResponse[LiquidacionEdificacionOut]) */
export const liquidacionEdificacionOutResponseSchema = apiResponseSchema(
  liquidacionEdificacionOutPayloadSchema,
);
