/**
 * Tipos para Liquidaciones Edificaciones — API contracts.
 */

// ── Lista Paginada ────────────────────────────────────────────────────────────

export interface LiquidacionListItem {
  id: string;
  public_id?: string;
  numero_revision: number;
  estado: string;
  municipalidad_id?: string | null;
  municipalidad_nombre?: string | null;
  tipo_tramite?: TipoTramiteEdificaciones;
  tramite_accion?: TramiteAccion;
  valor_proyecto: number;
  proyecto_public_id: string;
  proyecto_denominacion: string;
  fecha_registro: string;
  total: number;
}

export interface PaginatedLiquidaciones {
  items: LiquidacionListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Variables Financieras ─────────────────────────────────────────────────────

export interface VariablesFinancieras {
  igv_valor: number;
  igv_periodo_inicio: string;
  uit_valor: number;
  uit_periodo_inicio: string;
}

// ── Formulario ────────────────────────────────────────────────────────────────

export interface PrimeraRevisionFormData {
  proyecto_public_id: string;
  municipalidad_id: string;
  tipo_tramite: TipoTramiteEdificaciones;
  valor_proyecto: number;
  observacion?: string;
  revisiones_ids: string[];
  proyectistas_ids: string[];
}

export type TipoTramiteEdificaciones =
  | "OBRA_NUEVA"
  | "DEMOLICION"
  | "AMPLIACION"
  | "REMODELACION"
  | "MODIFICACION_LICENCIA";

export type TramiteAccion = "PRIMERA_REVISION" | "REVISION";

export interface ProvinciaBasic {
  id: string;
  nombre: string;
}

export interface DistritoBasic {
  id: string;
  nombre: string;
}

export interface MunicipalidadOption {
  id: string;
  nombre: string;
  codigo: string | null;
  provincia: ProvinciaBasic | null;
  distrito: DistritoBasic | null;
}

// ── Snapshot / Detalle ────────────────────────────────────────────────────────

export interface SnapshotTarifa {
  id: string;
  derecho_minimo: string;
  derecho_maximo: string | null;
  porcentaje_minimo_uit: string;
}

export interface SnapshotRevision {
  id: string;
  numero_revision: number;
  especialidad: string;
  tarifa: SnapshotTarifa;
  monto_base: number;
  cobra: boolean;
}

export interface SnapshotTotales {
  subtotal: number;
  igv: number;
  total: number;
  liquidacion_total: number;
  total_a_pagar: number;
}

export interface SnapshotProyecto {
  id: string;
  public_id: string;
  nombre: string;
  direccion: string;
  valor_proyecto: number;
  entidad: {
    id: string;
    tipo: string;
    nombre: string;
    ruc: string;
  } | null;
}

export interface SnapshotLiquidacion {
  id: string;
  public_id: string;
  estado: string;
  fecha_creacion: string;
  proyecto: SnapshotProyecto;
  municipalidad_id: string;
  municipalidad_nombre: string;
  observacion: string;
}

export interface SnapshotProyectista {
  id: string;
  cip: string | null;
  dni: string;
  cap: string | null;
  nombres: string;
  apellidos: string;
}

export interface SnapshotEdificaciones {
  public_id: string;
  numero_revision: number;
  tipo_tramite: TipoTramiteEdificaciones;
  tramite_accion: TramiteAccion;
  proyectistas: SnapshotProyectista[];
  revisiones: SnapshotRevision[];
}

export interface LiquidacionSnapshotMetadata {
  igv_valor: number;
  uit_valor: number;
  cobra: boolean;
}

export interface LiquidacionSnapshot {
  liquidacion: SnapshotLiquidacion;
  edificaciones: SnapshotEdificaciones;
  totales: SnapshotTotales;
  _metadata?: LiquidacionSnapshotMetadata;
}

// ── Estado Modal ──────────────────────────────────────────────────────────────

export type LiquidacionFormMode =
  | { mode: "closed" }
  | { mode: "create" };


// ── Snapshot List (cards) ──────────────────────────────────────────────────────

export interface SnapshotTarifaCard {
  id: string;
  derecho_minimo: number;
  derecho_maximo: number | null;
  porcentaje_minimo_uit: number;
}

export interface SnapshotRevisionCard {
  id: string;
  numero_revision: number;
  especialidad: string;
  tarifa: SnapshotTarifaCard;
  monto_base: number;
  cobra: boolean;
}

export interface SnapshotTotalesCard {
  subtotal: number;
  igv: number;
  total: number;
  liquidacion_total: number;
  total_a_pagar: number;
}

export interface SnapshotEntidadCard {
  id: string;
  tipo: string | null;
  nombre: string | null;
  ruc: string | null;
}

export interface SnapshotProyectistaCard {
  id: string;
  cip: string | null;
  dni: string | null;
  cap: string | null;
  nombres: string;
  apellidos: string;
}

export interface SnapshotProyectoCard {
  id: string;
  public_id: string;
  nombre: string;
  direccion: string | null;
  valor_proyecto: number;
  entidad: SnapshotEntidadCard | null;
}

export interface SnapshotEdificacionesCard {
  public_id: string;
  numero_revision: number;
  tipo_tramite: TipoTramiteEdificaciones;
  tramite_accion: TramiteAccion;
  proyectistas: SnapshotProyectistaCard[];
  revisiones: SnapshotRevisionCard[];
}

export interface LiquidacionSnapshotListItem {
  liquidacion_id: string;
  public_id: string;
  numero_liquidacion: string;
  estado: string;
  fecha_registro: string;
  municipalidad_id: string | null;
  municipalidad_nombre: string | null;
  observacion: string | null;
  proyecto: SnapshotProyectoCard;
  edificaciones: SnapshotEdificacionesCard;
  totales: SnapshotTotalesCard;
}

export interface PaginatedLiquidacionSnapshots {
  items: LiquidacionSnapshotListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Cotización / Quote ────────────────────────────────────────────────────────

export interface CotizacionTarifa {
  id: string;
  derecho_minimo: number;
  derecho_maximo: number | null;
  porcentaje_minimo_uit: number;
}

export interface CotizacionRevision {
  id: string;
  especialidad: string;
  tarifa: CotizacionTarifa;
  monto_base: number;
  cobra: boolean;
}

export interface CotizacionTotales {
  subtotal: number;
  igv: number;
  total: number;
  liquidacion_total: number;
  total_a_pagar: number;
}

export interface CotizacionMetadata {
  igv_valor: number;
  uit_valor: number;
  cobra: boolean;
}

export interface CotizacionQuote {
  numero_revision: number;
  revisiones: CotizacionRevision[];
  totales: CotizacionTotales;
  _metadata: CotizacionMetadata;
}
