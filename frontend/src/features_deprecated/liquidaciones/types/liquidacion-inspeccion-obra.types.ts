/**
 * Tipos para Inspección de Obra — API contracts.
 * Endpoint base: /liquidaciones/inspeccion-obra
 */
import type { ContactoInline } from "./contacto";

// Re-export ContactoInline for convenience
export type { ContactoInline } from "./contacto";

// ── Categorías ─────────────────────────────────────────────────────────────────

export const CATEGORIAS_IO = ["C1", "C2", "C3", "C4"] as const;
export type CategoriaIO = (typeof CATEGORIAS_IO)[number];

// ── Kind Constant ───────────────────────────────────────────────────────────────

export const INSPECCION_OBRA_KIND = "inspeccion-obra" as const;
export type InspeccionObraKind = typeof INSPECCION_OBRA_KIND;

// ── Entidad Inline (IO-specific) ──────────────────────────────────────────────

export interface EntidadInline {
  tipo_documento: string;
  numero_documento: string;
  razon_social: string;
}

// ── Proyecto Inline (IO-specific) ──────────────────────────────────────────────

export interface ProyectoInline {
  denominacion: string;
  direccion?: string;
  distrito_id?: string;
  nombre_propietario: string;
  entidad: EntidadInline;
}

// ── Input Types ────────────────────────────────────────────────────────────────

export interface CrearInspeccionObraPrimeraRevisionIn {
  liquidacion_previa_id?: string;
  proyecto_public_id?: string;
  proyecto_inline?: ProyectoInline;
  municipalidad_id?: string;
  cantidad_visitas: number;
  categoria: CategoriaIO;
  expediente?: string;
  observacion?: string;
  tarifas_ids: string[];
  contactos: ContactoInline[];
  inspectores_ids?: string[];
}

// ── Cotizar Types ─────────────────────────────────────────────────────────────

export interface CotizarInspeccionObraPrimeraRevisionIn {
  cantidad_visitas: number;
  categoria: CategoriaIO;
  tarifas_ids: string[];
}

export interface CotizacionIOTarifa {
  id: string;
  costo_por_visita: number;
  visitas_minimas: number;
}

export interface CotizacionIOCalculo {
  cantidad_visitas: number;
  visitas_base_calculo: number;
  derecho: number;
  categoria: string;
  tarifa: CotizacionIOTarifa;
}

export interface CotizacionIOTotales {
  subtotal: number;
  igv: number;
  total: number;
  liquidacion_total: number;
  total_a_pagar: number;
}

export interface CotizacionIOMetadata {
  igv_valor: number;
  uit_valor: number;
  cantidad_visitas?: number;
}

export interface CotizacionIOResponse {
  numero_revision: number;
  calculo_visitas: CotizacionIOCalculo;
  totales: CotizacionIOTotales;
  _metadata: CotizacionIOMetadata;
}

// ── Crear Response ────────────────────────────────────────────────────────────

export type CrearInspeccionObraResponse = LiquidacionInspeccionObraListItem;

// ── Domain-specific liquidacion_tipo ─────────────────────────────────────────

/**
 * liquidacion_tipo for Inspección de Obra — Visitas calculation.
 */
export interface LiquidacionInspeccionObraTipo {
  id: string;
  cantidad_visitas: number;
  porcentaje_uit: number;
  categoria: string;
  tarifa_aplicada_id: string;
}

// ── List Types ────────────────────────────────────────────────────────────────

import type { LiquidacionInspeccionObraListItem } from "../schemas/liquidacion-inspeccion-obra.schema";

export type { LiquidacionInspeccionObraListItem };

/** Paginated response for IO list endpoint */
export interface LiquidacionesInspeccionObraPaginated {
  items: LiquidacionInspeccionObraListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Tarifa Vigente ────────────────────────────────────────────────────────────

export interface TarifaVigenteInspeccionObra {
  tarifa_id: string;
  costo_por_visita: number;
  visitas_minimas: number;
  categoria: string;
  habilitada: boolean;
}
