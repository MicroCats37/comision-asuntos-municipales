/**
 * Tipos para Inspección de Obra — API contracts.
 * Endpoint base: /liquidaciones/inspeccion-obra
 */
import type { ContactoInline } from "./contacto";

// Re-export ContactoInline for convenience
export type { ContactoInline } from "./contacto";

// ── Entidad Inline (IO-specific) ──────────────────────────────────────────────

/**
 * Entidad inline para creación de proyecto inline en Inspección de Obra.
 * Coincide con la estructura del backend para el campo `entidad` dentro de `proyecto_inline`.
 */
export interface EntidadInline {
  tipo_documento: string;
  numero_documento: string;
  razon_social: string;
}

// ── Proyecto Inline (IO-specific) ──────────────────────────────────────────────

/**
 * Proyecto inline para creación en línea de Inspección de Obra.
 * Coincide con la estructura del backend para `proyecto_inline`.
 */
export interface ProyectoInline {
  denominacion: string;
  direccion?: string;
  distrito_id?: string;
  nombre_propietario: string;
  entidad: EntidadInline;
}

// ── Kind Constant ───────────────────────────────────────────────────────────────

export const INSPECCION_OBRA_KIND = "inspeccion-obra" as const;
export type InspeccionObraKind = typeof INSPECCION_OBRA_KIND;

// ── Categorías ─────────────────────────────────────────────────────────────────

/**
 * Categorías disponibles para inspección de obra.
 */
export const CATEGORIAS_IO = ["C1", "C2", "C3", "C4"] as const;

export type CategoriaIO = (typeof CATEGORIAS_IO)[number];

// ── Input Types ────────────────────────────────────────────────────────────────

/**
 * Input para crear primera revisión de Inspección de Obra.
 */
export interface CrearInspeccionObraPrimeraRevisionIn {
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

// ── Cotizar Types ─────────────────────────────────────────────────────────────

/**
 * Payload para cotizar primera revisión de Inspección de Obra.
 */
export interface CotizarInspeccionObraPrimeraRevisionIn {
  cantidad_visitas: number;
  categoria: CategoriaIO;
  // municipalidad_id NO es requerida para cotizar; solo para creación final
  tarifas_ids: string[];
}

// ── Cotizar Response ───────────────────────────────────────────────────────────

/**
 * Tarifa en respuesta de cotización de Inspección de Obra.
 */
export interface CotizacionIOTarifa {
  id: string;
  costo_por_visita: number;
  visitas_minimas: number;
}

/**
 * Cálculo en respuesta de cotización de Inspección de Obra.
 */
export interface CotizacionIOCalculo {
  cantidad_visitas: number;
  visitas_base_calculo: number;
  derecho: number;
  categoria: string;
  tarifa: CotizacionIOTarifa;
}

/**
 * Totales en respuesta de cotización.
 */
export interface CotizacionIOTotales {
  subtotal: number;
  igv: number;
  total: number;
  liquidacion_total: number;
  total_a_pagar: number;
}

/**
 * Metadata en respuesta de cotización.
 */
export interface CotizacionIOMetadata {
  igv_valor: number;
  uit_valor: number;
  cantidad_visitas?: number;
}

/**
 * Respuesta de cotización de Inspección de Obra.
 */
export interface CotizacionIOResponse {
  numero_revision: number;
  calculo_visitas: CotizacionIOCalculo;
  totales: CotizacionIOTotales;
  _metadata: CotizacionIOMetadata;
}

// ── Crear Response ────────────────────────────────────────────────────────────

/**
 * Respuesta de creación de Inspección de Obra.
 * Now returns the flat list item shape with all related data for immediate post-create PDF.
 */
export type CrearInspeccionObraResponse = LiquidacionInspeccionObraListItem;

// ── Nested Types for List Items ──────────────────────────────────────────────

export interface ProyectoListItem {
  id: string;
  public_id: string;
  nombre: string;
  direccion: string | null;
  valor_proyecto: number;
  entidad: EntidadListItem;
}

export interface EntidadListItem {
  id: string | null;
  tipo: string | null;
  nombre: string | null;
  ruc: string | null;
}

export interface MunicipalidadListItem {
  id: string;
  nombre: string;
  codigo: string | null;
  provincia: null;
  distrito: null;
}

export interface ValoresListItem {
  subtotal: number;
  igv: number;
  total: number;
  total_a_pagar: number;
}

export interface ProyectistaListItem {
  id: string;
  perfil_ingeniero_id: string | null;
  perfil_ingeniero_nombres: string | null;
  perfil_ingeniero_apellidos: string | null;
  perfil_ingeniero_cip: string | null;
  especialidad_id: string | null;
  especialidad_nombre: string | null;
  descripcion: string | null;
}

export interface DelegadoListItem {
  id: string;
  perfil_ingeniero_id: string | null;
  perfil_ingeniero_nombres: string | null;
  perfil_ingeniero_apellidos: string | null;
  perfil_ingeniero_cip: string | null;
  especialidad_id: string | null;
  especialidad_nombre: string | null;
  tipo: string | null;
}

export interface ContactoListItem {
  id: string;
  nombres: string | null;
  apellidos: string | null;
  dni: string | null;
  cargo: string | null;
  telefono: string | null;
  celular: string | null;
  email: string | null;
  direccion: string | null;
  principal: boolean;
  descripcion: string | null;
}

export interface TarifaRevisionListItem {
  id: string;
  // IO fields
  costo_por_visita?: number | null;
  visitas_minimas?: number | null;
  categoria?: string | null;
  // cantidad de visitas solicitada (populated by backend)
  cantidad_visitas?: number | null;
}

export interface EspecialidadRevisionListItem {
  id: string;
  nombre: string;
}

export interface RevisionListItem {
  id: string;
  especialidades: EspecialidadRevisionListItem[];
  tarifa: TarifaRevisionListItem;
}

// ── List Types ────────────────────────────────────────────────────────────────

/**
 * Item de lista para Inspección de Obra.
 */
export interface LiquidacionInspeccionObraListItem {
  id: string;
  public_id: string;
  estado: string;
  tipo_liquidacion: string;
  numero_revision: number;
  fecha_registro: string;
  proyecto: ProyectoListItem;
  entidad: EntidadListItem;
  municipalidad: MunicipalidadListItem;
  valores: ValoresListItem;
  proyectistas: ProyectistaListItem[];
  delegados: DelegadoListItem[];
  contactos: ContactoListItem[];
  revisiones: RevisionListItem[];
}

/**
 * Respuesta paginada de lista de Inspección de Obra.
 */
export interface LiquidacionesInspeccionObraPaginated {
  items: LiquidacionInspeccionObraListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Tarifa Vigente ────────────────────────────────────────────────────────────

/**
 * Tarifa vigente para Inspección de Obra.
 */
export interface TarifaVigenteInspeccionObra {
  tarifa_id: string;
  costo_por_visita: number;
  visitas_minimas: number;
  categoria: string;
  habilitada: boolean;
}
