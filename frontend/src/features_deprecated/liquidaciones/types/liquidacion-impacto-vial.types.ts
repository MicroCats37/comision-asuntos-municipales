/**
 * Tipos para Impacto Vial — API contracts.
 * Endpoint base: /liquidaciones/impacto-vial
 */
import type { ContactoInline } from "./contacto";

// Re-export ContactoInline for convenience
export type { ContactoInline } from "./contacto";

// ── Kind Constant ───────────────────────────────────────────────────────────────

export const IMPACTO_VIAL_KIND = "impacto-vial" as const;
export type ImpactoVialKind = typeof IMPACTO_VIAL_KIND;

// ── Entidad Inline (IV-specific) ──────────────────────────────────────────────

export interface EntidadInline {
  tipo_documento: string;
  numero_documento: string;
  razon_social: string;
}

// ── Proyecto Inline (IV-specific) ──────────────────────────────────────────────

export interface ProyectoInline {
  denominacion: string;
  direccion?: string;
  distrito_id?: string;
  nombre_propietario: string;
  entidad: EntidadInline;
}

// ── Input Types ────────────────────────────────────────────────────────────────

export interface CrearImpactoVialPrimeraRevisionIn {
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

export interface CotizarImpactoVialPrimeraRevisionIn {
  valor_proyecto: number;
  tarifas_ids: string[];
}

export interface CotizacionImpactoVialTarifa {
  id: string;
  derecho_minimo: number;
  derecho_maximo: number | null;
  porcentaje_minimo_uit: number;
  porcentaje_liquidacion: number;
}

export interface CotizacionImpactoVialRevision {
  id: string;
  especialidades: Array<{ id: string; nombre: string }>;
  tarifa: CotizacionImpactoVialTarifa;
  monto_base: number;
  cobra: boolean;
}

export interface CotizacionImpactoVialTotales {
  subtotal: number;
  igv: number;
  total: number;
  liquidacion_total: number;
  total_a_pagar: number;
}

export interface CotizacionImpactoVialMetadata {
  igv_valor: number;
  uit_valor: number;
  cobra: boolean;
  valor_base_calculo: number;
}

export interface CotizacionImpactoVialResponse {
  numero_revision: number;
  revisiones: CotizacionImpactoVialRevision[];
  totales: CotizacionImpactoVialTotales;
  _metadata: CotizacionImpactoVialMetadata;
}

// ── Crear Response ────────────────────────────────────────────────────────────

export type CrearImpactoVialResponse = LiquidacionImpactoVialListItem;

// ── Domain-specific liquidacion_tipo ─────────────────────────────────────────

/**
 * Impacto Vial uses the same PorcentajeObra structure as Edificaciones.
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

export interface LiquidacionImpactoVialTipo {
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

import type { LiquidacionImpactoVialListItem } from "../schemas/liquidacion-impacto-vial.schema";

export type { LiquidacionImpactoVialListItem };

/** Paginated response for IV list endpoint */
export interface LiquidacionesImpactoVialPaginated {
  items: LiquidacionImpactoVialListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Tarifa Vigente ────────────────────────────────────────────────────────────

export interface TarifaVigenteImpactoVial {
  tarifa_id: string;
  porcentaje_liquidacion: number;
  derecho_minimo: number;
  derecho_maximo: number | null;
  porcentaje_minimo_uit: number;
  habilitada: boolean;
}
