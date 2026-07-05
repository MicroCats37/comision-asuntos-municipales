/**
 * Tipos para Liquidaciones No Edificación — API contracts.
 * Incluye: Habilitación Urbana, Mecánica de Suelos, Impacto Vial, Taludes, Inspección de Obra.
 */
import type { ContactoInline } from "./contacto";
export type { ContactoInline } from "./contacto";

// ── Tipos de Liquidación No Edificación ───────────────────────────────────────

/**
 * Tipos de liquidación no edificación.
 * HU = Habilitación Urbana
 * MS = Mecánica de Suelos
 * IV = Impacto Vial
 * T = Taludes
 * IO = Inspección de Obra
 */
export const LIQUIDACION_KINDS = [
  "habilitacion-urbana",
  "mecanica-suelos",
  "impacto-vial",
  "taludes",
  "inspeccion-obra",
] as const;

export type LiquidacionKind = (typeof LIQUIDACION_KINDS)[number];

/** Tipos M2: todos excepto inspección de obra */
export const LIQUIDACION_M2_KINDS = [
  "habilitacion-urbana",
  "mecanica-suelos",
  "impacto-vial",
  "taludes",
] as const;

export type LiquidacionM2Kind = (typeof LIQUIDACION_M2_KINDS)[number];

// ── Entidad Inline (referencia común) ─────────────────────────────────────────

export interface EntidadInline {
  tipo_documento: string;
  numero_documento: string;
  razon_social: string;
}

// ── Proyecto Inline (referencia común) ────────────────────────────────────────

export interface ProyectoInline {
  denominacion: string;
  direccion?: string;
  distrito_id?: string;
  nombre_propietario: string;
  entidad: EntidadInline;
}

// ── Base para M2 (HU, MS, IV, Taludes) ─────────────────────────────────────────

/**
 * Input para crear una liquidación M2-based (primera revisión).
 * Используется para: Habilitación Urbana, Mecánica de Suelos, Impacto Vial, Taludes.
 */
export interface LiquidacionM2BaseIn {
  /** ID del proyecto existente (XOR con proyecto_inline) */
  proyecto_public_id?: string;
  /** Datos del proyecto a crear inline (XOR con proyecto_public_id) */
  proyecto_inline?: ProyectoInline;
  /** ID de la municipalidad */
  municipalidad_id: string;
  /** Área solicitada en metros cuadrados */
  area_solicitada: number;
  /** Número de expediente (opcional) */
  expediente?: string;
  /** Observación adicional (opcional) */
  observacion?: string;
  /** IDs de tarifas a aplicar */
  tarifas_ids: string[];
  /** Lista de contactos asociados */
  contactos: ContactoInline[];
}

// ── Inspección de Obra (Visitas) ───────────────────────────────────────────────

/**
 * Categorías disponibles para inspección de obra.
 * Estas deben sincronizarse con el backend.
 */
export const CATEGORIAS_IO = ["C1", "C2", "C3", "C4"] as const;

export type CategoriaIO = (typeof CATEGORIAS_IO)[number];

/**
 * Input para crear una liquidación de Inspección de Obra (primera revisión).
 */
export interface CrearLiquidacionInspeccionObraIn {
  /** ID del proyecto existente (XOR con proyecto_inline) */
  proyecto_public_id?: string;
  /** Datos del proyecto a crear inline (XOR con proyecto_public_id) */
  proyecto_inline?: ProyectoInline;
  /** ID de la municipalidad */
  municipalidad_id: string;
  /** Cantidad de visitas requeridas */
  cantidad_visitas: number;
  /** Categoría de la inspección */
  categoria: CategoriaIO;
  /** Número de expediente (opcional) */
  expediente?: string;
  /** Observación adicional (opcional) */
  observacion?: string;
  /** IDs de tarifas a aplicar */
  tarifas_ids: string[];
  /** Lista de contactos asociados */
  contactos: ContactoInline[];
}

// ── Cotizar Request Payloads ───────────────────────────────────────────────────

/**
 * Payload para cotizar primera revisión M2.
 */
export interface CotizarM2PrimeraRevisionIn {
  tipo_liquidacion: LiquidacionM2Kind;
  area_solicitada: number;
  municipalidad_id: string;
  tarifas_ids: string[];
}

/**
 * Payload para cotizar primera revisión Inspección de Obra.
 */
export interface CotizarInspeccionObraPrimeraRevisionIn {
  cantidad_visitas: number;
  categoria: CategoriaIO;
  municipalidad_id: string;
  tarifas_ids: string[];
}

// ── Cotizar Response ───────────────────────────────────────────────────────────

/**
 * Totales en respuesta de cotización (both M2 and IO).
 */
export interface CotizacionTotalesNoEdificacion {
  subtotal: number;
  igv: number;
  total: number;
  liquidacion_total: number;
  total_a_pagar: number;
}

/**
 * Tarifa M2 en respuesta de cotización.
 */
export interface CotizacionM2Tarifa {
  id: string;
  costo_por_m2: number;
  area_minima: number;
  derecho_minimo: number;
  derecho_maximo: number | null;
}

/**
 * Cálculo M2 en respuesta de cotización.
 */
export interface CotizacionM2Calculo {
  area_solicitada: number;
  area_base_calculo: number;
  derecho: number;
  tarifa: CotizacionM2Tarifa;
}

/**
 * Metadata M2 en respuesta de cotización.
 */
export interface CotizacionM2Metadata {
  igv_valor: number;
  uit_valor: number;
  area_solicitada?: number;
}

/**
 * Respuesta de cotización M2 (HU, MS, IV, Taludes).
 */
export interface CotizacionM2Response {
  numero_revision: number;
  calculo_m2: CotizacionM2Calculo;
  totales: CotizacionTotalesNoEdificacion;
  _metadata: CotizacionM2Metadata;
}

/**
 * Tarifa IO en respuesta de cotización.
 */
export interface CotizacionIOTarifa {
  id: string;
  costo_por_visita: number;
  visitas_minimas: number;
}

/**
 * Cálculo IO (visitas) en respuesta de cotización.
 */
export interface CotizacionIOCalculo {
  cantidad_visitas: number;
  visitas_base_calculo: number;
  derecho: number;
  categoria: string;
  tarifa: CotizacionIOTarifa;
}

/**
 * Metadata IO en respuesta de cotización.
 */
export interface CotizacionIOMetadata {
  igv_valor: number;
  uit_valor: number;
  cantidad_visitas?: number;
}

/**
 * Respuesta de cotización Inspección de Obra.
 */
export interface CotizacionIOResponse {
  numero_revision: number;
  calculo_visitas: CotizacionIOCalculo;
  totales: CotizacionTotalesNoEdificacion;
  _metadata: CotizacionIOMetadata;
}

// ── Props Interfaces ────────────────────────────────────────────────────────────

export interface LiquidacionNoEdificacionFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  /** Tipo de liquidación (kind) */
  tipo: LiquidacionKind;
}

// ── Tarifas Vigentes (GET /tarifas-vigentes) ────────────────────────────────

/**
 * Tarifa M2 vigente para selector en formulario.
 */
export interface TarifaVigenteM2 {
  tarifa_id: string;
  detalle_id: string;
  costo_por_m2: number;
  area_minima: number;
  derecho_minimo: number;
  derecho_maximo: number | null;
  habilitada: boolean;
}

/**
 * Tarifa de inspección de obra vigente para selector en formulario.
 */
export interface TarifaVigenteVisita {
  tarifa_id: string;
  detalle_id: string;
  costo_por_visita: number;
  visitas_minimas: number;
  categoria: string;
  habilitada: boolean;
}

/**
 * Mapeo de tipo de liquidación (kind) → path del endpoint de tarifas vigentes.
 */
export const TARIFAS_VIGENTES_ENDPOINTS: Record<LiquidacionM2Kind, string> = {
  "habilitacion-urbana": "/liquidaciones/habilitacion-urbana/tarifas-vigentes",
  "mecanica-suelos": "/liquidaciones/mecanica-suelos/tarifas-vigentes",
  "impacto-vial": "/liquidaciones/impacto-vial/tarifas-vigentes",
  "taludes": "/liquidaciones/taludes/tarifas-vigentes",
};

export const TARIFA_VIGENTE_ENDPOINT_INSPECCION = "/liquidaciones/inspeccion-obra/tarifas-vigentes";


// ── List Response Types ────────────────────────────────────────────────────────

/**
 * Item de lista para liquidación no-edificación.
 */
export interface LiquidacionNoEdificacionListItem {
  id: string;
  public_id: string;
  estado: string;
  fecha_registro: string;
  expediente: string | null;
  observacion: string | null;
  municipalidad_id: string | null;
  municipalidad_nombre: string | null;
  /** Área para M2, cantidad_visitas para IO; null para edificaciones */
  valor_caracteristico: number | null;
  tipo_liquidacion: LiquidacionKind;
  proyecto_public_id: string | null;
  proyecto_denominacion: string | null;
  /** Totales financieros; null si no están disponibles */
  totales: {
    subtotal: number;
    igv: number;
    total: number;
    liquidacion_total: number;
    total_a_pagar: number;
  } | null;
}

/**
 * Respuesta paginada de lista de liquidaciones no-edificación.
 */
export interface LiquidacionesNoEdificacionPaginated {
  items: LiquidacionNoEdificacionListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
