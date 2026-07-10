/**
 * Tipos para Liquidaciones GENERALES — API contracts.
 * Estos tipos son compartidos por todos los tipos de liquidación.
 */

// ── Base interface for Card components ─────────────────────────────────────────

/**
 * Base mínima que LiquidacionGeneralCard necesita para renderizar.
 * Remove campos de Edificación (tipo_tramite, tramite_accion, expediente)
 * y campos financieros duplicados al root.
 */
export interface LiquidacionCardBase {
  id: string;
  public_id: string;
  estado: string;
  tipo_liquidacion: string;
  numero_revision: number;
  fecha_registro: string;
  proyecto: ProyectoListItem;
  entidad: EntidadListItem | null;
  municipalidad: MunicipalldadListItem;
  valores: ValoresListItem | ValoresM2ListItem;
  proyectistas: ProyectistaListItem[];
  delegados: DelegadoListItem[];
  contactos: ContactoListItem[];
  revisiones: RevisionListItemBase[];
  /** Expediente - solo presente en Edificacion, opcional para otros tipos */
  expediente?: string | null;
  /** Observacion - solo presente en Edificacion, opcional para otros tipos */
  observacion?: string | null;
}

/**
 * RevisionListItem sin monto_base/cobra - para uso en cards.
 */
export interface RevisionListItemBase {
  id: string;
  especialidades: EspecialidadRevisionListItem[];
  tarifa: TarifaRevisionListItem | null;
}

/**
 * Valores para M2 sin IGV - para uso en cards de MS/HU/IV/Taludes.
 */
export interface ValoresM2ListItem {
  subtotal: number;
  total_a_pagar: number;
}

// ── Nested sub-types ──────────────────────────────────────────────────────────

export interface EntidadListItem {
  id: string | null;
  tipo: string | null;
  nombre: string | null;
  ruc: string | null;
}

export interface ProyectoListItem {
  id: string;
  public_id: string;
  nombre: string;
  direccion: string | null;
  valor_proyecto: number;
  entidad: EntidadListItem | null;
}

export interface MunicipalldadListItem {
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
  // M2 fields (for HU, MS, IV, Taludes)
  costo_por_m2?: number | null;
  area_m2?: number | null;
  derecho_minimo?: number | null;
  derecho_maximo?: number | null;
  // IO fields (for Inspeccion Obra)
  costo_por_visita?: number | null;
  visitas_minimas?: number | null;
  categoria?: string | null;
  // Edificacion fields (for porcentaje-based calculation)
  porcentaje_liquidacion?: number | null;
  porcentaje_minimo_uit?: number | null;
  // IO: cantidad de visitas solicitada (populated by backend)
  cantidad_visitas?: number | null;
}

export interface EspecialidadRevisionListItem {
  id: string;
  nombre: string;
}

export interface RevisionListItem {
  id: string;
  especialidades: EspecialidadRevisionListItem[];
  tarifa: TarifaRevisionListItem | null;
}

// ── Main list item type ──────────────────────────────────────────────────────

/**
 * Item de lista para liquidaciones GENERALES (Phase 5 — estructura rica común).
 * Compartido por todos los tipos: HU, IO, MS, Tal, IV.
 */
export interface LiquidacionGeneralListItem {
  id: string;
  public_id: string;
  estado: string;
  tipo_liquidacion: string;
  numero_revision: number;
  fecha_registro: string;
  tramite_accion: string | null;
  tipo_tramite: string | null;
  expediente: string | null;
  observacion: string | null;
  proyecto: ProyectoListItem;
  entidad: EntidadListItem | null;
  municipalidad: MunicipalldadListItem;
  valores: ValoresListItem;
  proyectistas: ProyectistaListItem[];
  delegados: DelegadoListItem[];
  contactos: ContactoListItem[];
  revisiones: RevisionListItem[];
  subtotal: number;
  igv: number;
  total: number;
  total_a_pagar: number;
}

export interface PaginatedLiquidacionesGenerales {
  items: LiquidacionGeneralListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Detail types (LiquidacionGeneralOut) ──────────────────────────────────────

export interface ProyectoGeneral {
  id: string;
  public_id: string;
  nombre: string;
  direccion: string | null;
}

export interface EntidadGeneral {
  id: string | null;
  tipo: string | null;
  nombre: string | null;
  ruc: string | null;
}

/**
 * Detail response type for M2/IO liquidations.
 * Matches LiquidacionGeneralOut from backend.
 */
export interface LiquidacionGeneralOut {
  id: string;
  public_id: string;
  estado: string;
  tipo_liquidacion: string;
  numero_revision: number;
  fecha_registro: string;
  expediente: string | null;
  observacion: string | null;
  municipalidad_nombre: string | null;
  proyecto: ProyectoGeneral | null;
  entidad: EntidadGeneral | null;
  subtotal: number;
  igv: number;
  total: number;
  total_a_pagar: number;
}
