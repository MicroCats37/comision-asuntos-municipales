/**
 * Tipos para Liquidaciones GENERALES — API contracts.
 * Estos tipos son compartidos por todos los tipos de liquidación.
 * Matches EXACTLY what backend returns in liquidacion_general.
 */

// Re-export types from schema for convenience
export type {
  LiquidacionGeneralListItem,
  PaginatedLiquidacionesGenerales,
} from "../schemas/liquidacion-general.schema";

// Re-export InspectorVigente for component imports
export type { InspectorVigente } from "@/features/inspectores/types/inspectores.types";

/** Alias for LiquidacionGeneralListItem — shared base for liquidacion cards */
export type LiquidacionCardBase = LiquidacionGeneralListItem;

// ── Wrapper types matching backend 3-wrapper output ──────────────────────────────

/**
 * Shared wrapper for liquidacion_general — matches LiquidacionGeneralOutput from backend.
 */
export interface LiquidacionGeneralWrapper {
  id: string;
  municipalidad_id: string;
  usuario_creador: { id: string };
  fecha_registro: string;
  expediente: string;
  observacion: string | null;
  numero_revision: number;
  sub_total: number;
  total: number;
  igv_id: string | null;
  uit_id: string | null;
  proyecto: {
    id: string;
    denominacion: string;
    nombre_propietario: string;
    direccion: string;
    distrito_id: string;
    entidad: {
      tipo_documento: string;
      numero_documento: string;
      razon_social: string;
    } | null;
  };
}

/**
 * Shared wrapper for liquidacion_especifica — matches LiquidacionTipoOutput from backend.
 */
export interface LiquidacionEspecificaWrapper {
  id: string;
  numero: number;
}

/**
 * Generic list item — T is the domain-specific liquidacion_tipo.
 * Matches the backend's 3-wrapper output pattern.
 */
export interface LiquidacionListItem<T> {
  liquidacion_general: LiquidacionGeneralWrapper;
  liquidacion_especifica: LiquidacionEspecificaWrapper;
  liquidacion_tipo: T;
}

// ── Variables financieras usadas ─────────────────────────────────────────────

/**
 * Variables financieras (IGV/UIT) usadas al momento de crear la liquidación.
 * Historicas, almacenadas en la liquidacion via FK a IGV/UIT.
 */
export interface VariablesFinancierasUsadas {
  igv_valor: number;
  igv_porcentaje: number;
  igv_periodo_inicio: string | null;
  uit_valor: number;
  uit_anio: number | null;
  uit_periodo_inicio: string | null;
}
