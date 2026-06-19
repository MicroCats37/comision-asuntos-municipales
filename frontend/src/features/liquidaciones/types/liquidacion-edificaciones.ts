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
  // numero_revision fue removido de cada revisión — solo existe en nivel edificaciones
  especialidad: string;
  tarifa: SnapshotTarifa;
  monto_base: number;
  cobra: boolean;
  // NOTE: derecho not present in backend RevisionOut for crearNuevaRevision
}

export interface SnapshotTotales {
  subtotal: number;
  igv: number;
  total: number;
  liquidacion_total: number;
  total_a_pagar: number;
}

export interface SnapshotProvincia {
  id: string;
  nombre: string;
}

export interface SnapshotDistrito {
  id: string;
  nombre: string;
  provincia: SnapshotProvincia | null;
}

export interface SnapshotMunicipalidad {
  id: string;
  nombre: string;
  codigo: string | null;
  // NOTE: backend presenter sets provincia=None and distrito=None explicitly
  provincia: SnapshotProvincia | null;
  distrito: SnapshotDistrito | null;
}

export interface SnapshotProyecto {
  id: string;
  public_id: string;
  nombre: string;
  direccion: string;
  valor_proyecto: number;
  // NOTE: backend EntidadOut has all optional fields
  entidad: {
    id: string | null;
    tipo: string | null;
    nombre: string | null;
    ruc: string | null;
  } | null;
  // NOTE: distrito not present in backend ProyectoOut for crearNuevaRevision
}

export interface SnapshotLiquidacion {
  id: string;
  public_id: string;
  estado: string;
  fecha_creacion: string;
  proyecto: SnapshotProyecto;
  municipalidad: SnapshotMunicipalidad;
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
  // NOTE: _metadata not present in backend LiquidacionSnapshotOut for crearNuevaRevision
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
  // numero_revision fue removido de cada revisión — solo existe en nivel edificaciones
  especialidad: string;
  tarifa: SnapshotTarifaCard;
  monto_base: number;
  cobra: boolean;
  derecho?: number | null | undefined;
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

export interface SnapshotProvinciaCard {
  id: string;
  nombre: string;
}

export interface SnapshotDistritoCard {
  id: string;
  nombre: string;
  provincia: SnapshotProvinciaCard | null;
}

export interface SnapshotMunicipalidadCard {
  id: string;
  nombre: string;
  codigo: string | null;
  provincia: SnapshotProvinciaCard | null;
  distrito: SnapshotDistritoCard | null;
}

export interface SnapshotProyectoCard {
  id: string;
  public_id: string;
  nombre: string;
  direccion: string | null;
  valor_proyecto: number;
  entidad: SnapshotEntidadCard | null;
  distrito?: SnapshotDistritoCard | null | undefined;
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
  municipalidad: SnapshotMunicipalidadCard;
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

// ── Nueva Revisión ────────────────────────────────────────────────────────────

/**
 * Proyectista actual — returned in formulario GET for nueva revision.
 * Reuses SnapshotProyectista shape.
 */
export interface ProyectistaActual {
  id: string;
  cip: string | null;
  dni: string;
  cap: string | null;
  nombres: string;
  apellidos: string;
}

/**
 * Revision Vigente as returned in the formulario response (same shape as RevisionVigente).
 * Used when revisiones_vigentes is embedded in NuevaRevisionFormularioResponse.
 */
export interface NuevaRevisionFormularioRevisionVigente {
  id: string;
  especialidad_id: string;
  especialidad_nombre: string;
  tarifa_id: string;
  porcentaje_liquidacion: number;
  derecho_minimo: number;
  derecho_maximo: number | null;
  porcentaje_minimo_uit: number;
  habilitada: boolean;
}

/**
 * Response payload from GET /liquidaciones/edificaciones/nueva-revision/formulario
 * Returns inherited fields from prior liquidacion plus available proyectistas.
 */
export interface NuevaRevisionFormularioResponse {
  liquidacion_previa_id: string;
  numero_revision: number;
  cobra: boolean;
  proyecto_id: string;
  proyecto_public_id: string;
  proyecto_nombre: string;
  valor_proyecto: number;
  /** Revisiones vigentes available for this project — same shape as RevisionVigente[] */
  revisiones_vigentes: NuevaRevisionFormularioRevisionVigente[];
  proyectistas_actuales: ProyectistaActual[];
}

/**
 * Form data for creating a nueva revision.
 * Passed to POST /liquidaciones/edificaciones/nueva-revision
 */
export interface NuevaRevisionFormData {
  liquidacion_previa_id: string;
  revisiones_ids: string[];
  proyectistas_ids: string[];
  observacion?: string;
}
