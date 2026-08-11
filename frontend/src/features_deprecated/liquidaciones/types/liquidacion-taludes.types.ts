/**
 * Tipos para Taludes — API contracts.
 * Endpoint base: /liquidaciones/taludes
 */
import type { ContactoInline } from "./contacto";

// Re-export ContactoInline for convenience
export type { ContactoInline } from "./contacto";

// ── Kind Constant ───────────────────────────────────────────────────────────────

export const TALUDES_KIND = "taludes" as const;
export type TaludesKind = typeof TALUDES_KIND;

// ── Entidad Inline (Taludes-specific) ──────────────────────────────────────────────

export interface EntidadInline {
  tipo_documento: string;
  numero_documento: string;
  razon_social: string;
}

// ── Proyecto Inline (Taludes-specific) ──────────────────────────────────────────────

export interface ProyectoInline {
  denominacion: string;
  direccion?: string;
  distrito_id?: string;
  nombre_propietario: string;
  entidad: EntidadInline;
}

// ── Input Types ────────────────────────────────────────────────────────────────

export interface CrearTaludesPrimeraRevisionIn {
  proyecto_public_id?: string;
  proyecto_inline?: ProyectoInline;
  municipalidad_id: string;
  valor_proyecto: number;
  expediente?: string;
  observacion?: string;
  tarifas_ids: string[];
  contactos: ContactoInline[];
}

// ── Cotizar Types ─────────────────────────────────────────────────────────────

export interface CotizarTaludesPrimeraRevisionIn {
  valor_proyecto: number;
  tarifas_ids: string[];
}

export interface CotizacionTaludesTarifa {
  id: string;
  derecho_minimo: number;
  derecho_maximo: number | null;
  porcentaje_minimo_uit: number;
  porcentaje_liquidacion: number;
}

export interface CotizacionTaludesRevision {
  id: string;
  especialidades: Array<{ id: string; nombre: string }>;
  tarifa: CotizacionTaludesTarifa;
  monto_base: number;
  cobra: boolean;
}

export interface CotizacionTaludesTotales {
  subtotal: number;
  igv: number;
  total: number;
  liquidacion_total: number;
  total_a_pagar: number;
}

export interface CotizacionTaludesMetadata {
  igv_valor: number;
  uit_valor: number;
  cobra: boolean;
  valor_base_calculo: number;
}

export interface CotizacionTaludesResponse {
  numero_revision: number;
  revisiones: CotizacionTaludesRevision[];
  totales: CotizacionTaludesTotales;
  _metadata: CotizacionTaludesMetadata;
}

// ── Crear Response ────────────────────────────────────────────────────────────

export type CrearTaludesResponse = LiquidacionTaludesListItem;

// ── Domain-specific liquidacion_tipo ─────────────────────────────────────────

/**
 * Taludes uses the same PorcentajeObra structure as Edificaciones.
 */
export interface LiquidacionTipoDetalle {
  id: string;
  tarifa_aplicada_id: string;
  especialidad_id: string;
  porcentaje_aplicado: number;
  subtotal: number;
  igv: number;
  uit: number;
  total: number;
}

export interface LiquidacionTaludesTipo {
  id: string;
  valor_declarado: number;
  porcentaje_liquidacion: number;
  tipo_tramite: string | null;
  derecho_minimo: number | null;
  derecho_maximo: number | null;
  porcentaje_minimo_uit: number;
  derecho_aplicado_id: string;
  detalles: LiquidacionTipoDetalle[];
}

// ── List Types ────────────────────────────────────────────────────────────────

import type { LiquidacionTaludesListItem } from "../schemas/liquidacion-taludes.schema";

export type { LiquidacionTaludesListItem };

/** Paginated response for Taludes list endpoint */
export interface LiquidacionesTaludesPaginated {
  items: LiquidacionTaludesListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Tarifa Vigente ────────────────────────────────────────────────────────────

export interface TarifaVigenteTaludes {
  tarifa_id: string;
  porcentaje_liquidacion: number;
  derecho_minimo: number;
  derecho_maximo: number | null;
  porcentaje_minimo_uit: number;
  habilitada: boolean;
}
