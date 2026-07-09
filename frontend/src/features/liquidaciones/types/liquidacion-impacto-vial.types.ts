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
 * Payload para cotizar primera revisión de Impacto Vial.
 */
export interface CotizarImpactoVialPrimeraRevisionIn {
  area_solicitada: number;
  municipalidad_id: string;
  tarifas_ids: string[];
}

// ── Cotizar Response ───────────────────────────────────────────────────────────

/**
 * Tarifa en respuesta de cotización de Impacto Vial.
 */
export interface CotizacionImpactoVialTarifa {
  id: string;
  costo_por_m2: number;
  area_minima: number;
  derecho_minimo: number;
  derecho_maximo: number | null;
}

/**
 * Cálculo en respuesta de cotización de Impacto Vial.
 */
export interface CotizacionImpactoVialCalculo {
  area_solicitada: number;
  area_base_calculo: number;
  derecho: number;
  tarifa: CotizacionImpactoVialTarifa;
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
 */
export interface CotizacionImpactoVialMetadata {
  igv_valor: number;
  uit_valor: number;
  area_solicitada?: number;
}

/**
 * Respuesta de cotización de Impacto Vial.
 */
export interface CotizacionImpactoVialResponse {
  numero_revision: number;
  calculo_m2: CotizacionImpactoVialCalculo;
  totales: CotizacionImpactoVialTotales;
  _metadata: CotizacionImpactoVialMetadata;
}

// ── Crear Response ────────────────────────────────────────────────────────────

/**
 * Respuesta de creación de Impacto Vial.
 */
export interface CrearImpactoVialResponse {
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
  tarifa: TarifaRevisionListItem;
  monto_base: number;
  cobra: boolean;
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
  tramite_accion: string | null;
  tipo_tramite: string | null;
  expediente: string | null;
  observacion: string | null;
  proyecto: ProyectoListItem;
  entidad: EntidadListItem;
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
 * Tarifa vigente para Impacto Vial.
 */
export interface TarifaVigenteImpactoVial {
  tarifa_id: string;
  detalle_id: string;
  costo_por_m2: number;
  area_minima: number;
  derecho_minimo: number;
  derecho_maximo: number | null;
  habilitada: boolean;
}
