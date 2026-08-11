/**
 * Tipos para Habilitación Urbana — API contracts.
 * Endpoint base: /liquidaciones/habilitacion-urbana
 */
import type { ContactoInline } from "./contacto";

// Re-export ContactoInline for convenience
export type { ContactoInline } from "./contacto";

// ── Kind Constant ───────────────────────────────────────────────────────────────

export const HABILITACION_URBANA_KIND = "habilitacion-urbana" as const;
export type HabilitacionUrbanaKind = typeof HABILITACION_URBANA_KIND;

// ── Entidad Inline (HU-specific) ──────────────────────────────────────────────

export interface EntidadInline {
  tipo_documento: string;
  numero_documento: string;
  razon_social: string;
}

// ── Proyecto Inline (HU-specific) ──────────────────────────────────────────────

export interface ProyectoInline {
  denominacion: string;
  direccion?: string;
  distrito_id?: string;
  nombre_propietario: string;
  entidad: EntidadInline;
}

// ── Input Types ────────────────────────────────────────────────────────────────

export interface CrearHabilitacionUrbanaPrimeraRevisionIn {
  proyecto_public_id?: string;
  proyecto_inline?: ProyectoInline;
  municipalidad_id: string;
  area_solicitada: number;
  expediente?: string;
  observacion?: string;
  tarifas_ids: string[];
  contactos: ContactoInline[];
}

// ── Cotizar Types ─────────────────────────────────────────────────────────────

export interface CotizarHabilitacionUrbanaPrimeraRevisionIn {
  area_solicitada: number;
  tarifas_ids: string[];
}

export interface CotizacionHabilitacionUrbanaTarifa {
  id: string;
  costo_por_m2: number;
  area_m2: number;
  derecho_minimo: number;
  derecho_maximo: number | null;
}

export interface CotizacionHabilitacionUrbanaCalculo {
  area_solicitada: number;
  area_base_calculo: number;
  derecho: number;
  tarifa: CotizacionHabilitacionUrbanaTarifa;
}

export interface CotizacionHabilitacionUrbanaTotales {
  subtotal: number;
  igv: number;
  total: number;
  liquidacion_total: number;
  total_a_pagar: number;
}

export interface CotizacionHabilitacionUrbanaMetadata {
  igv_valor: number;
  uit_valor: number;
  area_solicitada?: number;
}

export interface CotizacionHabilitacionUrbanaResponse {
  numero_revision: number;
  calculo_m2: CotizacionHabilitacionUrbanaCalculo;
  totales: CotizacionHabilitacionUrbanaTotales;
  _metadata: CotizacionHabilitacionUrbanaMetadata;
}

// ── Crear Response ────────────────────────────────────────────────────────────

export type CrearHabilitacionUrbanaResponse = LiquidacionHabilitacionUrbanaListItem;

// ── Domain-specific liquidacion_tipo ─────────────────────────────────────────

/**
 * Habilitación Urbana uses the same MetroCuadrado structure as Mecánica de Suelos.
 */
export interface LiquidacionM2Tipo {
  id: string;
  area_m2: number;
  costo_por_m2: number;
  derecho_minimo: number;
  derecho_maximo: number;
  tarifa_aplicada_id: string;
  derecho_aplicado_id: string;
}

// ── List Types ────────────────────────────────────────────────────────────────

import type { LiquidacionHabilitacionUrbanaListItem } from "../schemas/liquidacion-habilitacion-urbana.schema";

export type { LiquidacionHabilitacionUrbanaListItem };

/** Paginated response for HU list endpoint */
export interface LiquidacionesHabilitacionUrbanaPaginated {
  items: LiquidacionHabilitacionUrbanaListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Tarifa Vigente ────────────────────────────────────────────────────────────

export interface TarifaVigenteHabilitacionUrbana {
  tarifa_id: string;
  costo_por_m2: number;
  area_m2: number;
  derecho_minimo: number;
  derecho_maximo: number | null;
  habilitada: boolean;
}
