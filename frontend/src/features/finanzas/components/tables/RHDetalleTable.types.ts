/**
 * Shared row types for RH Detalle tables (Delegados + Inspectores).
 * These mirror the flat/nested shape returned by the backend hooks
 * and are used to populate the CSS-grid table rows.
 */

import type { LucideIcon } from "lucide-react";

// ── Shared structure ────────────────────────────────────────────────────────────

export interface RHDetalleLiquidacionInfo {
  id: string;
  expediente?: string | null;
  numero_revision?: number | null;
  numero?: number | null;
  municipalidad?: {
    id?: string;
    nombre?: string | null;
  } | null | undefined;
  tipo_liquidacion?: {
    id?: string;
    codigo?: string | null;
    nombre?: string | null;
  } | null | undefined;
}

export interface RHDetallePersonaInfo {
  id: string;
  cip?: string | null;
  nombre_completo?: string | null;
}

// ── Delegados ─────────────────────────────────────────────────────────────────

/** Nested shape from `useRHDetalleDelegados` */
export interface DetalleDelegadoRow {
  id: string;
  imp_bruto?: number | null;
  sub_total?: number | null;
  renta_cip?: number | null;
  aporte_codemu?: number | null;
  fondo_comun?: number | null;
  neto_honorario?: number | null;
  delegado_liquidacion?: {
    id: string;
    periodo?: number | null;
    mes?: number | null;
    delegado: RHDetallePersonaInfo;
    liquidacion: RHDetalleLiquidacionInfo;
    especialidad?: {
      id: string;
      nombre?: string | null;
    } | null | undefined;
  } | null;
}

/** Flat row shape used internally by RHDetalleDelegadosTable */
export interface RHDetalleDelegadoRow {
  id: string;
  liquidacionId: string | null;
  expediente: string | null;
  numeroRevision: number | null;
  numero: number | null;
  delegadoNombre: string | null;
  delegadoCip: string | null;
  periodo: string | null;
  mes: number | null;
  municipalidadNombre: string | null;
  tipoCodigo: string | null;
  tipoNombre: string | null;
  impBruto: number | null;
  rentaCip: number | null;
  aporteCodem: number | null;
  fondoComun: number | null;
  neto: number | null;
}

export function formatDelegadoRow(row: DetalleDelegadoRow): RHDetalleDelegadoRow {
  const dl = row.delegado_liquidacion;
  return {
    id: row.id,
    liquidacionId: dl?.liquidacion?.id ?? null,
    expediente: dl?.liquidacion?.expediente ?? null,
    numeroRevision: dl?.liquidacion?.numero_revision ?? null,
    numero: dl?.liquidacion?.numero ?? null,
    delegadoNombre: dl?.delegado?.nombre_completo ?? null,
    delegadoCip: dl?.delegado?.cip ?? null,
    periodo: dl?.periodo != null ? String(dl.periodo) : null,
    mes: dl?.mes ?? null,
    municipalidadNombre: dl?.liquidacion?.municipalidad?.nombre ?? null,
    tipoCodigo: dl?.liquidacion?.tipo_liquidacion?.codigo ?? null,
    tipoNombre: dl?.liquidacion?.tipo_liquidacion?.nombre ?? null,
    impBruto: row.imp_bruto ?? null,
    rentaCip: row.renta_cip ?? null,
    aporteCodem: row.aporte_codemu ?? null,
    fondoComun: row.fondo_comun ?? null,
    neto: row.neto_honorario ?? null,
  };
}

// ── Inspectores ───────────────────────────────────────────────────────────────

/** Nested shape from `useRHDetalleInspectores` */
export interface DetalleInspectorRow {
  id: string;
  inspecciones_liquidadas?: number | null;
  costo_por_inspeccion?: number | null;
  monto_contribuido?: number | null;
  saldo_restante?: number | null;
  importe_bruto?: number | null;
  sub_total?: number | null;
  descuento?: number | null;
  honorarios?: number | null;
  tasa_descuento?: number | null;
  inspector_liquidacion?: {
    id: string;
    periodo?: number | null;
    mes?: number | null;
    inspector: RHDetallePersonaInfo;
    liquidacion: RHDetalleLiquidacionInfo;
  } | null;
}

/** Flat row shape used internally by RHDetalleInspectoresTable */
export interface RHDetalleInspectorRow {
  id: string;
  liquidacionId: string | null;
  expediente: string | null;
  numeroRevision: number | null;
  numero: number | null;
  inspectorNombre: string | null;
  inspectorCip: string | null;
    periodo: number | null;
    mes: number | null;
  municipalidadNombre: string | null;
  tipoCodigo: string | null;
  inspLiq: number | null;
  costoInsp: number | null;
  montoContrib: number | null;
  subTotal: number | null;
  descuento: number | null;
  honorarios: number | null;
}

export function formatInspectorRow(
  row: DetalleInspectorRow,
): RHDetalleInspectorRow {
  const il = row.inspector_liquidacion;
  return {
    id: row.id,
    liquidacionId: il?.liquidacion?.id ?? null,
    expediente: il?.liquidacion?.expediente ?? null,
    numeroRevision: il?.liquidacion?.numero_revision ?? null,
    numero: il?.liquidacion?.numero ?? null,
    inspectorNombre: il?.inspector?.nombre_completo ?? null,
    inspectorCip: il?.inspector?.cip ?? null,
    periodo: il?.periodo ?? null,
    mes: il?.mes ?? null,
    municipalidadNombre: il?.liquidacion?.municipalidad?.nombre ?? null,
    tipoCodigo: il?.liquidacion?.tipo_liquidacion?.codigo ?? null,
    inspLiq: row.inspecciones_liquidadas ?? null,
    costoInsp: row.costo_por_inspeccion ?? null,
    montoContrib: row.monto_contribuido ?? null,
    subTotal: row.sub_total ?? null,
    descuento: row.descuento ?? null,
    honorarios: row.honorarios ?? null,
  };
}

// ── Shared table constants ─────────────────────────────────────────────────────

export const RH_TABLE_COL_ACTIONS = 160;
export const RH_TABLE_COL_ID = 200;

export const RH_DELEGADOS_GRID_TEMPLATE =
  `[actions]${RH_TABLE_COL_ACTIONS}px [id]${RH_TABLE_COL_ID}px [expediente]minmax(160px,1fr) [delegado]minmax(200px,1.5fr) [periodo]120px [imp_bruto]120px [renta_cip]120px [aporte_codemu]120px [fondo_comun]120px [neto]120px`;

export const RH_INSPECTORES_GRID_TEMPLATE =
  `[actions]${RH_TABLE_COL_ACTIONS}px [id]${RH_TABLE_COL_ID}px [expediente]minmax(160px,1fr) [inspector]minmax(200px,1.5fr) [periodo]120px [insp_liq]100px [costo]120px [monto]120px [subtotal]120px [descuento]120px [honorarios]120px`;

// ── Action button helpers ──────────────────────────────────────────────────────

export interface RHDetalleRowAction {
  icon: LucideIcon;
  label: string;
  onAction: () => void;
  variant?: "default" | "primary";
  hidden?: boolean;
}
