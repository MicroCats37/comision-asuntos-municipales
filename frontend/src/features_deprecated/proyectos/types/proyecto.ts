/**
 * Tipos para Proyectos — API contracts.
 *
 * Based on backend ProyectoListItemOut from:
 * backend/modules/liquidaciones/presentation/schemas/proyecto_schemas.py
 */

// ── Entidad Anidada ───────────────────────────────────────────────────────────

export interface EntidadWithNumeroDocumento {
  id: string | null;
  tipo_documento: string | null; // RUC o DNI
  numero_documento: string | null;
  nombre: string | null;
}

// ── Edificaciones Inline ───────────────────────────────────────────────────────

export interface EdificacionListItem {
  id: string;
  public_id: string;
  numero_revision: number;
  estado: string;
  fecha_registro: string;
  total: number;
  tipo_tramite: string;
  tramite_accion: string;
}

export interface LiquidacionesInline {
  edificaciones: EdificacionListItem[];
}

// ── Proyecto List Item ────────────────────────────────────────────────────────

export interface ProyectoListItem {
  id: string;
  public_id: string;
  denominacion: string;
  direccion: string | null;
  distrito: string | null;
  entidad: EntidadWithNumeroDocumento | null;
  liquidaciones: LiquidacionesInline;
}

// ── Paginated Response ────────────────────────────────────────────────────────

export interface PaginatedProyectos {
  items: ProyectoListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
