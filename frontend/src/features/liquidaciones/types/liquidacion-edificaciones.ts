/**
 * Tipos para Liquidaciones Edificaciones — API contracts.
 */

// ── Lista Paginada ────────────────────────────────────────────────────────────

export interface LiquidacionListItem {
  id: string;
  public_id: string | null;
  numero_revision: number;
  estado: string;
  municipalidad_id: string | null;
  municipalidad_nombre: string | null;
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

/**
 * Item de lista para liquidaciones GENERALES (backend Phase 4+).
 * Endpoint: GET /liquidaciones
 *
 * Diferencias con LiquidacionListItem (Edificaciones):
 * - No tiene valor_proyecto, municipalidad_id, municipalidad_nombre
 * - Usa tipo_liquidacion en lugar de tipo_tramite/tramite_accion
 */
export interface LiquidacionGeneralListItem {
  id: string;
  public_id: string | null;
  estado: string;
  tipo_liquidacion: string;
  numero_revision: number;
  proyecto_denominacion: string | null;
  proyecto_public_id: string | null;
  fecha_registro: string;
  total: number;
}

export interface PaginatedLiquidacionesGenerales {
  items: LiquidacionGeneralListItem[];
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

/**
 * Inline proyectista for liquidacion submit.
 */
export interface ProyectistaSubmit {
  cip: string;
  especialidad_id: string;
  descripcion?: string;
}

// Proyecto Inline para crear al vuelo
export interface ProyectoInline {
  denominacion: string;
  direccion?: string;
  distrito_id?: string;
  entidad_id?: string | null;
}

export interface PrimeraRevisionFormData {
  // XOR: uno de los dos es requerido
  proyecto_public_id?: string;
  proyecto_inline?: ProyectoInline;
  municipalidad_id: string;
  tipo_tramite: TipoTramiteEdificaciones;
  valor_proyecto: number;
  observacion?: string;
  revisiones_ids: string[];
  proyectistas: ProyectistaSubmit[];
  // delegadas_ids fue eliminado del payload de creación
  // tarifas_ids es opcional para compatibilidad con formularios deprecated
  tarifas_ids?: string[];
}

export type TipoTramiteEdificaciones =
  | "OBRA_NUEVA"
  | "DEMOLICION"
  | "AMPLIACION"
  | "REMODELACION"
  | "MODIFICACION_LICENCIA"
  | "REINTEGRO"
  | "PROYECTO_CON_PLANTAS_TIPICAS";

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
  // NOTE: especialidades es M2M — lista de objetos {id, nombre}
  especialidades: EspecialidadBasica[];
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
  direccion: string | null;
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
  expediente: string | null;
  observacion: string | null;
  proyecto: SnapshotProyecto;
  municipalidad: SnapshotMunicipalidad;
}

export interface SnapshotProyectista {
  id: string;
  perfil_ingeniero_id: string;
  perfil_ingeniero_nombres: string;
  perfil_ingeniero_apellidos: string;
  perfil_ingeniero_cip: string;
  especialidad_id: string;
  especialidad_nombre: string;
  descripcion: string | null;
}

export interface SnapshotDelegado {
  id: string;
  perfil_ingeniero_id: string;
  perfil_ingeniero_nombres: string;
  perfil_ingeniero_apellidos: string;
  perfil_ingeniero_cip: string;
  especialidad_id: string;
  especialidad_nombre: string;
  tipo: string | null;
}

export interface SnapshotEdificaciones {
  public_id: string;
  numero_revision: number;
  tipo_tramite: TipoTramiteEdificaciones;
  tramite_accion: TramiteAccion;
  proyectistas: SnapshotProyectista[];
  delegados: SnapshotDelegado[];
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

// ── Flat LiquidacionEdificacionOut Types (Phase 4+) ────────────────────────────

/**
 * Especialidad anidada en revisión — coincide con EspecialidadOut del backend.
 */
export interface EspecialidadOut {
  id: string;
  nombre: string;
}

/**
 * Tarifa anidada en revisión — coincide con TarifaOut del backend.
 */
export interface TarifaOut {
  id: string;
  derecho_minimo: string | number;
  derecho_maximo: string | number | null;
  porcentaje_minimo_uit: string | number;
}

/**
 * Revisión anidada — coincide con RevisionOut del backend.
 */
export interface RevisionOut {
  id: string;
  especialidades: EspecialidadOut[];
  tarifa: TarifaOut;
  monto_base: string | number;
  cobra: boolean;
}

/**
 * Entidad anidada — coincide con EntidadOut del backend.
 */
export interface EntidadOut {
  id: string | null;
  tipo: string | null;
  nombre: string | null;
  ruc: string | null;
}

/**
 * Provincia básica anidada — coincide con ProvinciaBasicOut del backend.
 */
export interface ProvinciaBasicOut {
  id: string;
  nombre: string;
}

/**
 * Distrito básico anidado — coincide con DistritoBasicOut del backend.
 */
export interface DistritoBasicOut {
  id: string;
  nombre: string;
  provincia: ProvinciaBasicOut | null;
}

/**
 * Municipalidad anidada — coincide con MunicipalidadOut del backend.
 */
export interface MunicipalidadOut {
  id: string;
  nombre: string;
  codigo: string | null;
  provincia: ProvinciaBasicOut | null;
  distrito: DistritoBasicOut | null;
}

/**
 * Valores financieros anidados — coincide con ValoresOut del backend.
 */
export interface ValoresOut {
  subtotal: string | number;
  igv: string | number;
  total: string | number;
  total_a_pagar: string | number;
}

/**
 * Proyecto anidado — coincide con ProyectoOut del backend.
 */
export interface ProyectoOut {
  id: string;
  public_id: string;
  nombre: string;
  direccion: string | null;
  valor_proyecto: string | number;
  entidad: EntidadOut | null;
}

/**
 * Proyectista anidado — coincide con ProyectistaOut del backend.
 */
export interface ProyectistaOut {
  id: string;
  perfil_ingeniero_id: string | null;
  perfil_ingeniero_nombres: string | null;
  perfil_ingeniero_apellidos: string | null;
  perfil_ingeniero_cip: string | null;
  especialidad_id: string | null;
  especialidad_nombre: string | null;
  descripcion: string | null;
}

/**
 * Delegado anidado — coincide con DelegadoOut del backend.
 */
export interface DelegadoOut {
  id: string;
  perfil_ingeniero_id: string | null;
  perfil_ingeniero_nombres: string | null;
  perfil_ingeniero_apellidos: string | null;
  perfil_ingeniero_cip: string | null;
  especialidad_id: string | null;
  especialidad_nombre: string | null;
  tipo: string | null;
}

/**
 * Contacto anidado — coincide con ContactoEdificacionOut del backend.
 */
export interface ContactoOut {
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

/**
 * Respuesta plana de creación/detalle de edificación.
 * Coincide con LiquidacionEdificacionOut del backend:
 * - Estructura PLANA con objetos anidados (proyecto, municipalidad, valores, etc.)
 * - Campos financieros duplicados al nivel raíz (subtotal, igv, total, total_a_pagar)
 */
export interface LiquidacionEdificacionOut {
  id: string;
  public_id: string;
  estado: string;
  fecha_registro: string;
  expediente: string | null;
  observacion: string | null;
  numero_revision: number;
  tipo_tramite: TipoTramiteEdificaciones;
  tramite_accion: TramiteAccion;
  proyecto: ProyectoOut;
  entidad: EntidadOut | null;
  municipalidad: MunicipalidadOut;
  valores: ValoresOut;
  proyectistas: ProyectistaOut[];
  delegados: DelegadoOut[];
  contactos: ContactoOut[];
  revisiones: RevisionOut[];
  // Campos financieros directos (duplicados de valores para conveniencia)
  subtotal: string | number;
  igv: string | number;
  total: string | number;
  total_a_pagar: string | number;
}

/**
 * Respuesta paginada para lista de liquidaciones de edificaciones.
 * El backend retorna LiquidacionEdificacionOut completo en cada item de items[].
 */
export interface PaginatedLiquidacionesEdificaciones {
  items: LiquidacionEdificacionOut[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Estado Modal ──────────────────────────────────────────────────────────────

export type LiquidacionFormMode = { mode: "closed" } | { mode: "create" };

// ── Snapshot List (cards) ──────────────────────────────────────────────────────

export interface SnapshotTarifaCard {
  id: string;
  derecho_minimo: string | number;
  derecho_maximo: string | number | null;
  porcentaje_minimo_uit: string | number;
}

export interface SnapshotRevisionCard {
  id: string;
  // numero_revision fue removido de cada revisión — solo existe en nivel edificaciones
  // NOTE: especialidades es M2M — lista de objetos {id, nombre}
  especialidades: EspecialidadBasica[];
  tarifa: SnapshotTarifaCard;
  monto_base: string | number;
  cobra: boolean;
  derecho?: string | number | null | undefined;
}

export interface SnapshotTotalesCard {
  subtotal: string | number;
  igv: string | number;
  total: string | number;
  liquidacion_total: string | number;
  total_a_pagar: string | number;
}

export interface SnapshotEntidadCard {
  id: string | null;
  tipo: string | null;
  nombre: string | null;
  ruc: string | null;
}

export interface SnapshotProyectistaCard {
  id: string;
  perfil_ingeniero_id: string | null;
  perfil_ingeniero_nombres: string | null;
  perfil_ingeniero_apellidos: string | null;
  perfil_ingeniero_cip: string | null;
  especialidad_id: string | null;
  especialidad_nombre: string | null;
  descripcion: string | null;
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
  id: string | null;
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
  valor_proyecto: string | number;
  entidad: SnapshotEntidadCard | null;
  distrito?: SnapshotDistritoCard | null | undefined;
}

export interface SnapshotEdificacionesCard {
  public_id: string;
  numero_revision: number;
  tipo_tramite?: TipoTramiteEdificaciones;
  tramite_accion?: TramiteAccion;
  proyectistas: SnapshotProyectistaCard[];
  delegados: unknown[];
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
  especialidades: EspecialidadBasica[];
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
  valor_base_calculo: number;
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
export interface EspecialidadBasica {
  id: string;
  nombre: string;
}

export interface NuevaRevisionFormularioRevisionVigente {
  id: string;
  especialidades: EspecialidadBasica[];
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
  valor_base_calculo: number;
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

// ── Delegados Vigentes ────────────────────────────────────────────────────────

/**
 * Especialidad anidada en delegado vigente.
 */
export interface EspecialidadBasicaDelegado {
  id: string;
  nombre: string;
}

/**
 * Delegado vigente para selección en formulario.
 * Retornado por GET /liquidaciones/edificaciones/delegados/vigentes
 */
export interface DelegadoVigente {
  id: string;
  nombre_completo: string;
  cip: string;
  especialidad: EspecialidadBasicaDelegado;
  tipo: string;
}
