/**
 * Tipos para Liquidaciones Edificaciones — API contracts.
 */
import type { ContactoInline } from "./contacto";

// Re-export ContactoInline for convenience
export type { ContactoInline } from "./contacto";

// Re-export LiquidacionEdificacionOut from schema for list view consumption
export type { LiquidacionEdificacionOut } from "../schemas/liquidacion.schema";

// ── Domain-specific liquidacion_tipo ─────────────────────────────────────────

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

export interface LiquidacionEdificacionesTipo {
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

import type { LiquidacionEdificacionOut } from "../schemas/liquidacion.schema";

/** List item type — matches LiquidacionEdificacionOut from backend flat structure */
export type LiquidacionEdificacionesListItem = LiquidacionEdificacionOut;

// ── Tipo Tramite ─────────────────────────────────────────────────────────────

export type TipoTramiteEdificaciones =
  | "OBRA_NUEVA"
  | "DEMOLICION"
  | "AMPLIACION"
  | "REMODELACION"
  | "MODIFICACION_LICENCIA"
  | "REINTEGRO"
  | "PROYECTO_CON_PLANTAS_TIPICAS";

export type TramiteAccion = "PRIMERA_REVISION" | "REVISION";

// ── Variables Financieras ─────────────────────────────────────────────────────

export interface VariablesFinancieras {
  igv_valor: number;
  igv_periodo_inicio: string;
  uit_valor: number;
  uit_periodo_inicio: string;
}

// ── Formulario ────────────────────────────────────────────────────────────────

export interface ProyectistaSubmit {
  cip: string;
  especialidad_id: string;
  descripcion?: string;
}

export interface ProyectoInline {
  denominacion: string;
  direccion?: string;
  distrito_id?: string;
  entidad_id?: string | null;
}

export interface PrimeraRevisionFormData {
  proyecto_public_id?: string;
  proyecto_inline?: ProyectoInline;
  municipalidad_id: string;
  tipo_tramite: TipoTramiteEdificaciones;
  valor_proyecto: number;
  observacion?: string;
  revisiones_ids: string[];
  proyectistas: ProyectistaSubmit[];
  tarifas_ids?: string[];
}

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

// ── Cotización / Quote ────────────────────────────────────────────────────────

export interface CotizacionTarifa {
  id: string;
  derecho_minimo: number;
  derecho_maximo: number | null;
  porcentaje_minimo_uit: number;
  porcentaje_liquidacion: number;
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

// ── Snapshot / Detalle ────────────────────────────────────────────────────────

export interface EspecialidadBasica {
  id: string;
  nombre: string;
}

export interface SnapshotTarifa {
  id: string;
  derecho_minimo: string;
  derecho_maximo: string | null;
  porcentaje_minimo_uit: string;
  porcentaje_liquidacion: string | number;
}

export interface SnapshotRevision {
  id: string;
  especialidades: EspecialidadBasica[];
  tarifa: SnapshotTarifa;
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
  provincia: SnapshotProvincia | null;
  distrito: SnapshotDistrito | null;
}

export interface SnapshotProyecto {
  id: string;
  public_id: string;
  nombre: string;
  direccion: string | null;
  valor_proyecto: number;
  entidad: {
    id: string | null;
    tipo: string | null;
    nombre: string | null;
    ruc: string | null;
  } | null;
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
}

// ── Nueva Revisión ────────────────────────────────────────────────────────────

export interface ProyectistaActual {
  id: string;
  perfil_ingeniero_id?: string | null;
  perfil_ingeniero_nombres?: string | null;
  perfil_ingeniero_apellidos?: string | null;
  perfil_ingeniero_cip?: string | null;
  especialidad_id?: string | null;
  especialidad_nombre?: string | null;
  descripcion?: string | null;
  cip?: string | null;
  dni?: string;
  cap?: string | null;
  nombres?: string;
  apellidos?: string;
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

export interface NuevaRevisionFormularioResponse {
  liquidacion_previa_id: string;
  numero_revision: number;
  cobra: boolean;
  proyecto_id: string;
  proyecto_public_id: string;
  proyecto_nombre: string;
  valor_proyecto: number;
  valor_base_calculo: number;
  revisiones_vigentes: NuevaRevisionFormularioRevisionVigente[];
  proyectistas_actuales: ProyectistaActual[];
  tipo_tramite: string;
}

export interface NuevaRevisionFormData {
  liquidacion_previa_id: string;
  revisiones_ids: string[];
  proyectistas_ids: string[];
  contactos?: ContactoInline[];
  observacion?: string;
  tipo_tramite?: string;
}

// ── Delegados Vigentes ────────────────────────────────────────────────────────

export interface EspecialidadBasicaDelegado {
  id: string;
  nombre: string;
}

export interface DelegadoVigente {
  id: string;
  nombre_completo: string;
  cip: string;
  especialidad: EspecialidadBasicaDelegado;
  tipo: string;
}

// ── Estado Modal ──────────────────────────────────────────────────────────────

export type LiquidacionFormMode = { mode: "closed" } | { mode: "create" };
