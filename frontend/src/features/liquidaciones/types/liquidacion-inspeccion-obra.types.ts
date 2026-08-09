/**
 * Tipos para Inspección de Obra — API contracts.
 * Endpoint base: /liquidaciones/inspeccion-obra
 */
import type { ContactoInline } from "./contacto";
import type { VariablesFinancierasUsadas } from "./liquidacion-general";

// Re-export ContactoInline for convenience
export type { ContactoInline } from "./contacto";

// ── Tipos de schemas ────────────────────────────────────────────────────────────

/**
 * Tipo inferido del schema de lista general de liquidaciones.
 * Usado para items de buscar-previas que ahora retornan LiquidacionGeneralListItemOut.
 */
export type LiquidacionGeneralListItemOut = {
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
  proyecto: {
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
  };
  entidad: {
    id: string | null;
    tipo: string | null;
    nombre: string | null;
    ruc: string | null;
  } | null;
  municipalidad: {
    id: string;
    nombre: string;
    codigo: string | null;
    provincia: null;
    distrito: null;
  };
  valores: {
    subtotal: number;
    igv: number;
    total: number;
    total_a_pagar: number;
  };
  proyectistas: Array<{
    id: string;
    perfil_ingeniero_id: string | null;
    perfil_ingeniero_nombres: string | null;
    perfil_ingeniero_apellidos: string | null;
    perfil_ingeniero_cip: string | null;
    especialidad_id: string | null;
    especialidad_nombre: string | null;
    descripcion: string | null;
  }>;
  delegados: Array<{
    id: string;
    perfil_ingeniero_id: string | null;
    perfil_ingeniero_nombres: string | null;
    perfil_ingeniero_apellidos: string | null;
    perfil_ingeniero_cip: string | null;
    especialidad_id: string | null;
    especialidad_nombre: string | null;
    tipo: string | null;
  }>;
  inspectores: Array<{
    id: string;
    perfil_ingeniero_id: string | null;
    perfil_ingeniero_nombres: string | null;
    perfil_ingeniero_apellidos: string | null;
    perfil_ingeniero_cip: string | null;
    especialidad_id: string | null;
    especialidad_nombre: string | null;
    tipo_liquidacion: string | null;
    categoria: number | null;
    numero_registro: string | null;
    vigencia: string | null;
  }>;
  contactos: Array<{
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
  }>;
  revisiones: Array<{
    id: string;
    especialidades: Array<{ id: string; nombre: string }>;
    tarifa: {
      id: string;
    } | null;
  }>;
  subtotal: number;
  igv: number;
  total: number;
  total_a_pagar: number;
  variables_financieras_usadas: VariablesFinancierasUsadas | null;
};

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
 * Input para crear primera revisión de Inspección de Obra basada en liquidación previa.
 *
 * Phase 1+: IO siempre se crea basada en una liquidacion_previa_id.
 * Los campos proyecto_public_id, proyecto_inline y municipalidad_id se ignoran
 * porque se derivan de la liquidación previa. Se mantienen opcionales por
 * compatibilidad con código existente (deprecated).
 */
export interface CrearInspeccionObraPrimeraRevisionIn {
  /** ID de la liquidación previa (requerido en Phase 1+, opcional por ahora para compatibilidad) */
  liquidacion_previa_id?: string;
  /** DEPRECATED: ID del proyecto existente — se ignora en la creación */
  proyecto_public_id?: string;
  /** DEPRECATED: Datos del proyecto inline — se ignora en la creación */
  proyecto_inline?: ProyectoInline;
  /** DEPRECATED: ID de la municipalidad — se ignora en la creación */
  municipalidad_id?: string;
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
  /** IDs de inspectores a asociar durante la creación */
  inspectores_ids?: string[];
}

/**
 * Item de lista para buscar liquidaciones previas de IO.
 * Ahora coincide con LiquidacionGeneralListItemOut del backend
 * (tipos EDIFICACION y HABILITACION_URBANA).
 */
export type LiquidacionPreviaIOListItem = LiquidacionGeneralListItemOut;

/**
 * Respuesta paginada para búsqueda de liquidaciones previas de IO.
 * Ahora usa LiquidacionGeneralListItemOut como tipo de items.
 */
export interface LiquidacionesIOBuscadasPaginated {
  items: LiquidacionPreviaIOListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
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

export interface InspectorListItem {
  id: string;
  perfil_ingeniero_id: string | null;
  perfil_ingeniero_nombres: string | null;
  perfil_ingeniero_apellidos: string | null;
  perfil_ingeniero_cip: string | null;
  especialidad_id: string | null;
  especialidad_nombre: string | null;
  tipo_liquidacion: string | null;
  categoria: number | null;
  numero_registro: string | null;
  vigencia: string | null;
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
  inspectores: InspectorListItem[];
  contactos: ContactoListItem[];
  revisiones: RevisionListItem[];
  /** Variables financieras (IGV/UIT) usadas al momento de crear la liquidación */
  variables_financieras_usadas: VariablesFinancierasUsadas | null;
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
