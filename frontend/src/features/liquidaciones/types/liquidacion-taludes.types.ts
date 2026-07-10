/**
 * Tipos para Taludes — API contracts.
 * Endpoint base: /liquidaciones/taludes
 */
import type { ContactoInline } from "./contacto";

// Re-export ContactoInline for convenience
export type { ContactoInline } from "./contacto";

// ── Entidad Inline (Taludes-specific) ──────────────────────────────────────────────

/**
 * Entidad inline para creación de proyecto inline en Taludes.
 * Coincide con la estructura del backend para el campo `entidad` dentro de `proyecto_inline`.
 */
export interface EntidadInline {
  tipo_documento: string;
  numero_documento: string;
  razon_social: string;
}

// ── Proyecto Inline (Taludes-specific) ──────────────────────────────────────────────

/**
 * Proyecto inline para creación en línea de Taludes.
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

export const TALUDES_KIND = "taludes" as const;
export type TaludesKind = typeof TALUDES_KIND;

// ── Input Types ────────────────────────────────────────────────────────────────

/**
 * Input para crear primera revisión de Taludes.
 */
export interface CrearTaludesPrimeraRevisionIn {
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

// ── Cotizar Types ─────────────────────────────────────────────────────────────

/**
 * Payload para cotizar primera revisión de Taludes.
 * municipalidad_id NO es requerida para cotizar; solo para creación final.
 */
export interface CotizarTaludesPrimeraRevisionIn {
  area_solicitada: number;
  tarifas_ids: string[];
}

// ── Cotizar Response ───────────────────────────────────────────────────────────

/**
 * Tarifa en respuesta de cotización de Taludes.
 */
export interface CotizacionTaludesTarifa {
  id: string;
  costo_por_m2: number;
  area_m2: number;
  derecho_minimo: number;
  derecho_maximo: number | null;
}

/**
 * Cálculo en respuesta de cotización de Taludes.
 */
export interface CotizacionTaludesCalculo {
  area_solicitada: number;
  area_base_calculo: number;
  derecho: number;
  tarifa: CotizacionTaludesTarifa;
}

/**
 * Totales en respuesta de cotización.
 */
export interface CotizacionTaludesTotales {
  subtotal: number;
  igv: number;
  total: number;
  liquidacion_total: number;
  total_a_pagar: number;
}

/**
 * Metadata en respuesta de cotización.
 */
export interface CotizacionTaludesMetadata {
  igv_valor: number;
  uit_valor: number;
  area_solicitada?: number;
}

/**
 * Respuesta de cotización de Taludes.
 */
export interface CotizacionTaludesResponse {
  numero_revision: number;
  calculo_m2: CotizacionTaludesCalculo;
  totales: CotizacionTaludesTotales;
  _metadata: CotizacionTaludesMetadata;
}

// ── Crear Response ────────────────────────────────────────────────────────────

/**
 * Respuesta de creación de Taludes.
 */
export interface CrearTaludesResponse {
  liquidacion: {
    id: string;
    public_id: string;
    estado: string;
    fecha_creacion: string;
    expediente: string | null;
    observacion: string | null;
  };
  totales: {
    subtotal: number;
    igv: number;
    total: number;
    liquidacion_total: number;
    total_a_pagar: number;
  };
}

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
  // M2 fields
  costo_por_m2?: number | null;
  area_m2?: number | null;
  derecho_minimo?: number | null;
  derecho_maximo?: number | null;
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
 * Item de lista para Taludes.
 */
export interface LiquidacionTaludesListItem {
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
 * Respuesta paginada de lista de Taludes.
 */
export interface LiquidacionesTaludesPaginated {
  items: LiquidacionTaludesListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Tarifa Vigente ────────────────────────────────────────────────────────────

/**
 * Tarifa vigente para Taludes.
 */
export interface TarifaVigenteTaludes {
  tarifa_id: string;
  costo_por_m2: number;
  area_m2: number;
  derecho_minimo: number;
  derecho_maximo: number | null;
  habilitada: boolean;
}
