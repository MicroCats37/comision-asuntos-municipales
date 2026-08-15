/**
 * Tipos para Liquidaciones de Edificaciones — API contracts.
 * Matches backend LiquidacionEdificacionOut structure.
 */
import { z } from "zod";
import {
  TipoTramiteEdificacionesSchema,
  TramiteAccionSchema,
} from "../schemas/tramite.schema";
import {
  entidadInlineSchema,
  municipalidadInlineSchema,
  proyectoInlineSchema,
  revisionBasicaSchema,
  tipoLiquidacionSchema,
  valoresFinancierosSchema,
  variablesFinancierasSchema,
} from "./liquidacion-general.types";

// ── Tipo Tramite Enum ─────────────────────────────────────────────────────────

export {
  type TipoTramiteEdificaciones,
  TipoTramiteEdificacionesSchema as tipoTramiteEdificacionesSchema,
  type TramiteAccion,
  TramiteAccionSchema as tramiteAccionSchema,
} from "../schemas/tramite.schema";

// ── Domain-specific liquidacion_tipo ──────────────────────────────────────────

export const liquidacionEdificacionesDetalleSchema = z.object({
  id: z.string(),
  tarifa_aplicada_id: z.string(),
  especialidad_id: z.string(),
  porcentaje_aplicado: z.number(),
  subtotal: z.number(),
  igv: z.number(),
  uit: z.number(),
  total: z.number(),
});

export const liquidacionEdificacionesTipoSchema = z.object({
  id: z.string(),
  valor_declarado: z.number(),
  porcentaje_liquidacion: z.number(),
  tipo_tramite: TipoTramiteEdificacionesSchema.nullable(),
  derecho_minimo: z.number().nullable(),
  derecho_maximo: z.number().nullable(),
  porcentaje_minimo_uit: z.number(),
  derecho_aplicado_id: z.string(),
  detalles: z.array(liquidacionEdificacionesDetalleSchema),
});

export type LiquidacionEdificacionesTipo = z.infer<
  typeof liquidacionEdificacionesTipoSchema
>;

// ── Flat Output Type (matches backend LiquidacionEdificacionOut) ───────────────

export const liquidacionEdificacionOutSchema = z.object({
  id: z.string(),
  public_id: z.string(),
  estado: z.string(),
  tipo_liquidacion: tipoLiquidacionSchema,
  fecha_registro: z.string(),
  expediente: z.string().nullable(),
  observacion: z.string().nullable(),
  numero_revision: z.number(),
  tipo_tramite: TipoTramiteEdificacionesSchema,
  tramite_accion: TramiteAccionSchema,
  proyecto: proyectoInlineSchema,
  entidad: entidadInlineSchema.nullable(),
  municipalidad: municipalidadInlineSchema,
  valores: valoresFinancierosSchema,
  proyectistas: z.array(
    z.object({
      id: z.string(),
      perfil_ingeniero_id: z.string().nullable(),
      perfil_ingeniero_nombres: z.string().nullable(),
      perfil_ingeniero_apellidos: z.string().nullable(),
      perfil_ingeniero_cip: z.string().nullable(),
      especialidad_id: z.string().nullable(),
      especialidad_nombre: z.string().nullable(),
      descripcion: z.string().nullable(),
    }),
  ),
  delegados: z.array(
    z.object({
      id: z.string(),
      perfil_ingeniero_id: z.string().nullable(),
      perfil_ingeniero_nombres: z.string().nullable(),
      perfil_ingeniero_apellidos: z.string().nullable(),
      perfil_ingeniero_cip: z.string().nullable(),
      especialidad_id: z.string().nullable(),
      especialidad_nombre: z.string().nullable(),
      tipo: z.string().nullable(),
    }),
  ),
  inspectores: z
    .array(
      z.object({
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
      }),
    )
    .default([]),
  contactos: z.array(
    z.object({
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
    }),
  ),
  revisiones: z.array(revisionBasicaSchema),
  subtotal: z.number(),
  igv: z.number(),
  total: z.number(),
  total_a_pagar: z.number(),
  variables_financieras_usadas: variablesFinancierasSchema.nullable(),
});

export type LiquidacionEdificacionOut = z.infer<
  typeof liquidacionEdificacionOutSchema
>;

// ── List Item Type ────────────────────────────────────────────────────────────

export type LiquidacionEdificacionesListItem = LiquidacionEdificacionOut;

// ── 3-Wrapper List Item ───────────────────────────────────────────────────────

export interface LiquidacionEdificacionesWrapper {
  liquidacion_general: import("./liquidacion-general.types").LiquidacionGeneralWrapper;
  liquidacion_especifica: import("./liquidacion-general.types").LiquidacionEspecificaWrapper;
  liquidacion_tipo: LiquidacionEdificacionOut;
}

// ── Form Types ───────────────────────────────────────────────────────────────

export interface ProyectistaSubmit {
  cip: string;
  especialidad_id: string;
  descripcion?: string;
}

export interface ProyectoInline {
  denominacion: string;
  direccion?: string;
  distrito_id?: string;
  entidad_id?: string | null;
}

export const primeraRevisionFormSchema = z.object({
  proyecto_public_id: z.string().optional(),
  proyecto_inline: z
    .object({
      denominacion: z.string().min(1, "Denominación es requerida"),
      direccion: z.string().optional(),
      distrito_id: z.string().uuid("Distrito es requerido").optional(),
      entidad_id: z.string().uuid().optional().nullable(),
    })
    .optional(),
  municipalidad_id: z.string().uuid("Municipalidad es requerida"),
  tipo_tramite: TipoTramiteEdificacionesSchema,
  valor_proyecto: z.number().positive("Valor debe ser positivo"),
  observacion: z.string().optional(),
  revisiones_ids: z.array(z.string()).default([]),
  proyectistas: z
    .array(
      z.object({
        cip: z.string().min(1, "CIP es requerido"),
        especialidad_id: z.string().uuid("Especialidad es requerida"),
        descripcion: z.string().optional(),
      }),
    )
    .default([]),
  tarifas_ids: z.array(z.string().uuid()).default([]),
});

export type PrimeraRevisionFormData = z.infer<typeof primeraRevisionFormSchema>;

// ── Delegados Vigentes ────────────────────────────────────────────────────────

export type {
  DelegadoVigente,
  EspecialidadBasicaDelegado,
} from "../schemas/delegado-vigente.schema";

// ── Cotización Types ─────────────────────────────────────────────────────────

export interface CotizacionTarifa {
  id: string;
  derecho_minimo: number;
  derecho_maximo: number | null;
  porcentaje_minimo_uit: number;
  porcentaje_liquidacion: number;
}

export interface CotizacionRevision {
  id: string;
  especialidades: { id: string; nombre: string }[];
  tarifa: CotizacionTarifa;
  monto_base: number;
  cobra: boolean;
}

export interface CotizacionTotales {
  subtotal: number;
  igv: number;
  total: number;
  liquidacion_total: number;
  total_a_pagar: number;
}

export interface CotizacionMetadata {
  igv_valor: number;
  uit_valor: number;
  cobra: boolean;
  valor_base_calculo: number;
}

export interface CotizacionQuote {
  numero_revision: number;
  revisiones: CotizacionRevision[];
  totales: CotizacionTotales;
  _metadata: CotizacionMetadata;
}
