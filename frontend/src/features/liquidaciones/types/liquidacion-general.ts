/**
 * Tipos para Liquidaciones GENERALES — API contracts.
 * Estos tipos son compartidos por todos los tipos de liquidación.
 */

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
  derecho_minimo: number | null;
  derecho_maximo: number | null;
  porcentaje_minimo_uit: number | null;
}

export interface EspecialidadRevisionListItem {
  id: string;
  nombre: string;
}

export interface RevisionListItem {
  id: string;
  especialidades: EspecialidadRevisionListItem[];
  tarifa: TarifaRevisionListItem | null;
  monto_base: number;
  cobra: boolean;
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
  municipalidad: MunicipalidadListItem;
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
