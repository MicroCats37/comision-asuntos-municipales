/**
 * Tipos para Mecánica de Suelos — API contracts.
 * Endpoint base: /liquidaciones/mecanica-suelos
 */
import type { ContactoInline } from "./contacto";

// Re-export ContactoInline for convenience
export type { ContactoInline } from "./contacto";

// ── Kind Constant ───────────────────────────────────────────────────────────────

export const MECANICA_SUELOS_KIND = "mecanica-suelos" as const;
export type MecanicaSuelosKind = typeof MECANICA_SUELOS_KIND;

// ── Entidad Inline (MS-specific) ──────────────────────────────────────────────

export interface EntidadInline {
  tipo_documento: string;
  numero_documento: string;
  razon_social: string;
}

// ── Proyecto Inline (MS-specific) ──────────────────────────────────────────────

export interface ProyectoInline {
  denominacion: string;
  direccion?: string;
  distrito_id?: string;
  nombre_propietario: string;
  entidad: EntidadInline;
}

// ── Input Types ────────────────────────────────────────────────────────────────

export interface CrearMecanicaSuelosPrimeraRevisionIn {
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

export interface CotizarMecanicaSuelosPrimeraRevisionIn {
  area_solicitada: number;
  tarifas_ids: string[];
}

export interface CotizacionMecanicaSuelosTarifa {
  id: string;
  costo_por_m2: number;
  area_m2: number;
  derecho_minimo: number;
  derecho_maximo: number | null;
}

export interface CotizacionMecanicaSuelosCalculo {
  area_solicitada: number;
  area_base_calculo: number;
  derecho: number;
  tarifa: CotizacionMecanicaSuelosTarifa;
}

export interface CotizacionMecanicaSuelosTotales {
  subtotal: number;
  igv: number;
  total: number;
  liquidacion_total: number;
  total_a_pagar: number;
}

export interface CotizacionMecanicaSuelosMetadata {
  igv_valor: number;
  uit_valor: number;
  area_solicitada?: number;
}

export interface CotizacionMecanicaSuelosResponse {
  numero_revision: number;
  calculo_m2: CotizacionMecanicaSuelosCalculo;
  totales: CotizacionMecanicaSuelosTotales;
  _metadata: CotizacionMecanicaSuelosMetadata;
}

// ── Crear Response ────────────────────────────────────────────────────────────

export type CrearMecanicaSuelosResponse = LiquidacionMecanicaSuelosListItem;

// ── Domain-specific liquidacion_tipo ─────────────────────────────────────────

/**
 * liquidacion_tipo for Mecánica de Suelos — MetroCuadrado calculation.
 */
export interface LiquidacionMecanicaSuelosTipo {
  id: string;
  area_m2: number;
  costo_por_m2: number;
  derecho_minimo: number;
  derecho_maximo: number;
  tarifa_aplicada_id: string;
  derecho_aplicado_id: string;
}

// ── List Types ────────────────────────────────────────────────────────────────

import type { LiquidacionMecanicaSuelosListItem } from "../schemas/liquidacion-mecanica-suelos.schema";

export type { LiquidacionMecanicaSuelosListItem };

/** Paginated response for MS list endpoint */
export interface LiquidacionesMecanicaSuelosPaginated {
  items: LiquidacionMecanicaSuelosListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Tarifa Vigente ────────────────────────────────────────────────────────────

export interface TarifaVigenteMecanicaSuelos {
  tarifa_id: string;
  costo_por_m2: number;
  area_m2: number;
  derecho_minimo: number;
  derecho_maximo: number | null;
  habilitada: boolean;
}
