/**
 * Tipos para Impacto Vial — API contracts.
 * Endpoint base: /liquidaciones/impacto-vial
 */
import type { ContactoInline } from "./contacto";

// Re-export ContactoInline for convenience
export type { ContactoInline } from "./contacto";

// ── Entidad Inline (IV-specific) ──────────────────────────────────────────────

/**
 * Entidad inline para creación de proyecto inline en Impacto Vial.
 * Coincide con la estructura del backend para el campo `entidad` dentro de `proyecto_inline`.
 */
export interface EntidadInline {
  tipo_documento: string;
  numero_documento: string;
  razon_social: string;
}

// ── Proyecto Inline (IV-specific) ──────────────────────────────────────────────

/**
 * Proyecto inline para creación en línea de Impacto Vial.
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

export const IMPACTO_VIAL_KIND = "impacto-vial" as const;
export type ImpactoVialKind = typeof IMPACTO_VIAL_KIND;

// ── Input Types ────────────────────────────────────────────────────────────────

/**
 * Input para crear primera revisión de Impacto Vial.
 */
export interface CrearImpactoVialPrimeraRevisionIn {
  /** ID del proyecto existente (XOR con proyecto_inline) */
  proyecto_public_id?: string;
  /** Datos del proyecto a crear inline (XOR con proyecto_public_id) */
  proyecto_inline?: ProyectoInline;
  /** ID de la municipalidad */
  municipalidad_id: string;
  /** Valor del proyecto (S/) — reemplaza area_solicitada */
  valor_proyecto: number;
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
 * Payload para cotizar primera revisión de Impacto Vial.
 * municipalidad_id NO es requerida para cotizar; solo para creación final.
 */
export interface CotizarImpactoVialPrimeraRevisionIn {
  valor_proyecto: number;
  tarifas_ids: string[];
}

// ── Cotizar Response (percentage-based — matches Edificaciones CotizacionQuote) ──

/**
 * Tarifa en respuesta de cotización de Impacto Vial (porcentaje).
 * Note: now matches CotizacionTarifa from liquidacion-edificaciones.types.ts.
 */
export interface CotizacionImpactoVialTarifa {
  id: string;
  derecho_minimo: number;
  derecho_maximo: number | null;
  porcentaje_minimo_uit: number;
  porcentaje_liquidacion: number;
}

/**
 * Revisión en respuesta de cotización de Impacto Vial (porcentaje).
 * Matches CotizacionRevision from liquidacion-edificaciones.types.ts.
 */
export interface CotizacionImpactoVialRevision {
  id: string;
  especialidades: Array<{ id: string; nombre: string }>;
  tarifa: CotizacionImpactoVialTarifa;
  monto_base: number;
  cobra: boolean;
}

/**
 * Totales en respuesta de cotización.
 */
export interface CotizacionImpactoVialTotales {
  subtotal: number;
  igv: number;
  total: number;
  liquidacion_total: number;
  total_a_pagar: number;
}

/**
 * Metadata en respuesta de cotización.
 * Matches CotizacionMetadata from liquidacion-edificaciones.types.ts.
 */
export interface CotizacionImpactoVialMetadata {
  igv_valor: number;
  uit_valor: number;
  cobra: boolean;
  valor_base_calculo: number;
}

/**
 * Respuesta de cotización de Impacto Vial (porcentaje-based — matches CotizacionQuote).
 * Now uses the same shape as Edificaciones: revisiones[] instead of calculo.
 */
export interface CotizacionImpactoVialResponse {
  numero_revision: number;
  revisiones: CotizacionImpactoVialRevision[];
  totales: CotizacionImpactoVialTotales;
  _metadata: CotizacionImpactoVialMetadata;
}

// ── Crear Response ────────────────────────────────────────────────────────────

/**
 * Respuesta de creación de Impacto Vial.
 * Now returns the flat list item shape with all related data for immediate post-create PDF.
 */
export type CrearImpactoVialResponse = LiquidacionImpactoVialListItem;

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

export interface ValoresM2ListItem {
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
  // M2 fields (for HU, MS — not IV/Taludes which now use percentage)
  costo_por_m2?: number | null;
  area_m2?: number | null;
  derecho_minimo?: number | null;
  derecho_maximo?: number | null;
  // Percentage fields (for IV, Taludes — Edificaciones-style)
  porcentaje_liquidacion?: number | null;
  porcentaje_minimo_uit?: number | null;
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
 * Item de lista para Impacto Vial.
 */
export interface LiquidacionImpactoVialListItem {
  id: string;
  public_id: string;
  estado: string;
  tipo_liquidacion: string;
  numero_revision: number;
  fecha_registro: string;
  proyecto: ProyectoListItem;
  entidad: EntidadListItem;
  municipalidad: MunicipalidadListItem;
  valores: ValoresM2ListItem;
  proyectistas: ProyectistaListItem[];
  delegados: DelegadoListItem[];
  contactos: ContactoListItem[];
  revisiones: RevisionListItem[];
}

/**
 * Respuesta paginada de lista de Impacto Vial.
 */
export interface LiquidacionesImpactoVialPaginated {
  items: LiquidacionImpactoVialListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Tarifa Vigente ────────────────────────────────────────────────────────────

/**
 * Tarifa vigente para Impacto Vial (porcentaje-based).
 */
export interface TarifaVigenteImpactoVial {
  tarifa_id: string;
  porcentaje_liquidacion: number;
  derecho_minimo: number;
  derecho_maximo: number | null;
  porcentaje_minimo_uit: number;
  habilitada: boolean;
}
