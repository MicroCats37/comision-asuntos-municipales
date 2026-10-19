"use client";

import {
  Building2,
  ClipboardCheck,
  FlaskRound,
  type LucideIcon,
  Map as MapIcon,
  Move3d,
  Triangle,
} from "lucide-react";
import { type ReactNode, useCallback, useState } from "react";
import { formatDecimalPercent } from "@/utils/number-formatter";
import {
  CalculoM2,
  CalculoPorcentaje,
} from "../components/cards/CalculoDetail";
import { DelegadosListBySpecialty } from "../components/DelegadosSection";
import {
  composeDetalleSections,
  LiquidacionDetalleEdificacionesSection,
  LiquidacionDetalleHabilitacionUrbanaSection,
  LiquidacionDetalleImpactoVialSection,
  LiquidacionDetalleInspeccionObraSection,
  LiquidacionDetalleMecanicaSuelosSection,
  LiquidacionDetalleModal,
  LiquidacionDetalleTaludesSection,
} from "../components/detail";
import {
  ComprobanteFormModal,
  EliminarLiquidacionModal,
  LiquidacionEdificacionFormModal,
  LiquidacionHabilitacionUrbanaFormModal,
  LiquidacionImpactoVialFormModal,
  LiquidacionInspeccionObraFormModal,
  LiquidacionMecanicaSuelosFormModal,
  LiquidacionTaludesFormModal,
} from "../components/forms";
import { GestionarDelegadosModal } from "../components/GestionarDelegadosModal";
import { formatCurrency } from "../components/liquidacion-ui";
import type { PdfLiquidacionItem } from "../pdf/buildLiquidacionPdfElement";
import type { PdfTipoSlug } from "../pdf/LiquidacionPdfPreview";
import { printLiquidacionPreview } from "../pdf/LiquidacionPdfPreview";
import { buildExtraFieldRows } from "../pdf/liquidacionPdfHelpers";
import type { LiquidacionEdificacionesListItem } from "../schemas/liquidacion-edificaciones.schema";
import type { LiquidacionHabilitacionUrbanaListItem } from "../schemas/liquidacion-habilitacion-urbana.schema";
import type { LiquidacionImpactoVialListItem } from "../schemas/liquidacion-impacto-vial.schema";
import type { LiquidacionInspeccionObraListItem } from "../schemas/liquidacion-inspeccion-obra.schema";
import type { LiquidacionMecanicaSuelosListItem } from "../schemas/liquidacion-mecanica-suelos.schema";
import type { LiquidacionTaludesListItem } from "../schemas/liquidacion-taludes.schema";
import { canEditLiquidacion } from "../utils/canEditLiquidacion";
import { formatPublicId } from "../utils/formatPublicId";

const fmtCurrency = (v: number | null | undefined): string =>
  formatCurrency(v ?? 0);

// ── Tipos compartidos ─────────────────────────────────────────────────

export interface LiquidacionCardComprobante {
  tipo_comprobante?: string | null;
  serie?: string | null;
  numero?: string | null;
}

interface DistritoLike {
  nombre?: string | null;
  provincia?: { nombre?: string | null } | null;
  departamento?: { nombre?: string | null } | null;
}

interface ProyectoLike {
  direccion?: string | null;
  nombre_propietario?: string | null;
  entidad?: {
    razon_social?: string | null;
    numero_documento?: string | null;
  } | null;
  distrito?: DistritoLike | null;
}

interface MunicipalidadLike {
  codigo?: string | null;
  nombre?: string | null;
}

interface ComprobanteLike extends LiquidacionCardComprobante {
  activo?: boolean;
}

interface LiquidacionGeneralLike {
  id: string;
  estado?: string | null;
  fecha_registro: string;
  expediente?: string | null;
  denominacion_de_proyecto?: string | null;
  total?: number | null;
  sub_total?: number | null;
  uit?: { valor?: number | null } | null;
  comprobantes?: ComprobanteLike[] | null;
  proyecto: ProyectoLike;
  municipalidad?: MunicipalidadLike | null;
  delegados?: unknown[] | null;
  numero_revision?: number | null;
}

interface LiquidacionCardItemLike {
  liquidacion_general: LiquidacionGeneralLike;
  liquidacion_especifica: { numero: number };
  liquidacion_tipo: unknown;
}

interface EditFormModalProps<TItem> {
  item: TItem;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

interface DetalleModalProps<TItem> {
  item: TItem;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  publicId: string;
}

/**
 * ShellProps — shape returned by the hook and spread into
 * `LiquidacionCardShell`. Kept as a public type so callers don't need to
 * import the shell internals.
 */
export interface LiquidacionCardShellProps {
  kindIcon: LucideIcon;
  kindLabel?: string;
  publicId: string;
  estado?: string | null;
  entidadNombre: string;
  entidadDocumento?: string | null;
  proyectoNombre?: string | null;
  proyectoUbicacion?: string | null;
  municipalidadLabel: string;
  distritoLabel?: string;
  expediente?: string | null;
  direccion?: string | null;
  comprobanteActivo?: LiquidacionCardComprobante | null;
  total?: number;
  subTotal?: number | null;
  igvMonto?: number | null;
  fechaRegistro: string;
  numeroRevision?: number | null;
  showDelegados?: boolean;
  onDelegados?: () => void;
  onPrint?: () => void;
  canEdit?: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
  onComprobante?: () => void;
  onVerDetalle?: () => void;
  calculoSlot?: ReactNode;
  delegadosSlot?: ReactNode;
}

// ── Config por dominio ───────────────────────────────────────────────

export interface LiquidacionCardConfig<TItem> {
  domain:
    | "edificaciones"
    | "taludes"
    | "impacto-vial"
    | "habilitacion-urbana"
    | "mecanica-suelos"
    | "inspeccion-obra";
  kindIcon: LucideIcon;
  kindLabel: string;
  kindBadge: string;
  tipoSlug: string;
  tipoPdf: PdfTipoSlug;
  showDelegados: boolean;

  getComprobanteActivo: (item: TItem) => LiquidacionCardComprobante | null;
  getMunicipalidadLabel: (item: TItem) => string;
  getDistritoLabel: (item: TItem) => string;
  getEntidadNombre: (item: TItem) => string;
  getEntidadDocumento: (item: TItem) => string | null;
  getPdfItem: (item: TItem) => PdfLiquidacionItem;

  /** Lista de especialidades (solo PorcentajeObra). undefined para M2/Visitas. */
  getEspecialidades?: (
    item: TItem,
  ) => Array<string | null | undefined> | undefined;

  buildCalculoSlot: (item: TItem) => ReactNode | null;
  buildDelegadosSlot: (item: TItem) => ReactNode | null;

  buildEditFormModal: (props: EditFormModalProps<TItem>) => ReactNode;
  buildDetalleModal: (props: DetalleModalProps<TItem>) => ReactNode;
}

// ── Helpers comunes ──────────────────────────────────────────────────

function getComprobanteActivo(item: {
  liquidacion_general: { comprobantes?: ComprobanteLike[] | null };
}): LiquidacionCardComprobante | null {
  return item.liquidacion_general.comprobantes?.find((c) => c.activo) ?? null;
}

function getMunicipalidadLabel(item: {
  liquidacion_general: { municipalidad?: MunicipalidadLike | null };
}): string {
  const m = item.liquidacion_general.municipalidad;
  if (!m) return "—";
  return m.codigo ? `${m.codigo} - ${m.nombre ?? ""}` : (m.nombre ?? "—");
}

function getDistritoLabel(item: {
  liquidacion_general: { proyecto: { distrito?: DistritoLike | null } };
}): string {
  const d = item.liquidacion_general.proyecto.distrito;
  if (!d) return "—";
  return [d.nombre, d.provincia?.nombre, d.departamento?.nombre]
    .filter(Boolean)
    .join(" - ");
}

function getEntidadNombre(item: {
  liquidacion_general: {
    proyecto: { entidad?: { razon_social?: string | null } | null };
  };
}): string {
  return item.liquidacion_general.proyecto.entidad?.razon_social ?? "—";
}

function getEntidadDocumento(item: {
  liquidacion_general: {
    proyecto: { entidad?: { numero_documento?: string | null } | null };
  };
}): string | null {
  return item.liquidacion_general.proyecto.entidad?.numero_documento ?? null;
}

// ── Config: Edificaciones ────────────────────────────────────────────

export const EDIFICACIONES_CONFIG: LiquidacionCardConfig<LiquidacionEdificacionesListItem> =
  {
    domain: "edificaciones",
    kindIcon: Building2,
    kindLabel: "Edificaciones",
    kindBadge: "Edificación",
    tipoSlug: "edificacion",
    tipoPdf: "edificacion",
    showDelegados: true,

    getComprobanteActivo,
    getMunicipalidadLabel,
    getDistritoLabel,
    getEntidadNombre,
    getEntidadDocumento,
    getPdfItem: (item) => ({
      liquidacion_general: item.liquidacion_general as never,
      liquidacion_especifica: item.liquidacion_especifica as never,
      liquidacion_tipo: item.liquidacion_tipo as never,
    }),
    getEspecialidades: (item) =>
      item.liquidacion_tipo.detalles
        ?.map((d) => d.especialidad?.nombre)
        .filter((n): n is string => Boolean(n)),

    buildCalculoSlot: (item) => {
      const lt = item.liquidacion_tipo;
      const lg = item.liquidacion_general;
      return (
        <CalculoPorcentaje
          motor="porcentaje"
          valorDeclarado={lt.valor_declarado}
          porcentajeLiquidacion={lt.porcentaje_liquidacion}
          derechoMinimo={lt.derecho_minimo}
          uit={lg.uit?.valor}
          porcentajeMinimoUit={lt.porcentaje_minimo_uit}
          formatCurrency={fmtCurrency}
          formatDecimalPercent={formatDecimalPercent}
        />
      );
    },

    buildDelegadosSlot: (item) => {
      const lg = item.liquidacion_general;
      const lt = item.liquidacion_tipo;
      const especialidades = lt.detalles
        ?.map((d) => d.especialidad?.nombre)
        .filter((n): n is string => Boolean(n));
      if (lg.delegados && lg.delegados.length > 0) {
        return (
          <DelegadosListBySpecialty
            delegados={lg.delegados as never}
            especialidades={especialidades}
          />
        );
      }
      if (lt.detalles?.some((d) => d.especialidad?.nombre)) {
        return (
          <DelegadosListBySpecialty
            delegados={[]}
            especialidades={especialidades}
          />
        );
      }
      return null;
    },

    buildEditFormModal: ({ item, open, onOpenChange, onSuccess }) => (
      <LiquidacionEdificacionFormModal
        mode="edit"
        item={item}
        open={open}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
      />
    ),

    buildDetalleModal: ({ item, open, onOpenChange, publicId }) => (
      <LiquidacionDetalleModal
        open={open}
        onOpenChange={onOpenChange}
        kindBadge="Edificación"
        publicId={publicId}
        estado={item.liquidacion_general.estado}
        kindIcon={Building2}
      >
        {composeDetalleSections({
          lg: item.liquidacion_general,
          lt: item.liquidacion_tipo,
          tipoSection: (
            <LiquidacionDetalleEdificacionesSection
              liquidacionTipo={item.liquidacion_tipo}
            />
          ),
        })}
      </LiquidacionDetalleModal>
    ),
  };

// ── Config: Taludes ─────────────────────────────────────────────────

export const TALUDES_CONFIG: LiquidacionCardConfig<LiquidacionTaludesListItem> =
  {
    ...EDIFICACIONES_CONFIG,
    domain: "taludes",
    kindIcon: Triangle,
    kindLabel: "Taludes",
    kindBadge: "Taludes",
    tipoSlug: "taludes",
    tipoPdf: "taludes",

    getPdfItem: (item) => ({
      liquidacion_general: item.liquidacion_general as never,
      liquidacion_especifica: item.liquidacion_especifica as never,
      liquidacion_tipo: item.liquidacion_tipo as never,
    }),

    buildEditFormModal: ({ item, open, onOpenChange, onSuccess }) => (
      <LiquidacionTaludesFormModal
        mode="edit"
        item={item}
        open={open}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
      />
    ),

    buildDetalleModal: ({ item, open, onOpenChange, publicId }) => (
      <LiquidacionDetalleModal
        open={open}
        onOpenChange={onOpenChange}
        kindBadge="Taludes"
        publicId={publicId}
        estado={item.liquidacion_general.estado}
        kindIcon={Triangle}
      >
        {composeDetalleSections({
          lg: item.liquidacion_general,
          lt: item.liquidacion_tipo,
          tipoSection: (
            <LiquidacionDetalleTaludesSection
              liquidacionTipo={item.liquidacion_tipo}
            />
          ),
        })}
      </LiquidacionDetalleModal>
    ),
  };

// ── Config: Impacto Vial ────────────────────────────────────────────

export const IMPACTO_VIAL_CONFIG: LiquidacionCardConfig<LiquidacionImpactoVialListItem> =
  {
    ...EDIFICACIONES_CONFIG,
    domain: "impacto-vial",
    kindIcon: Move3d,
    kindLabel: "Impacto Vial",
    kindBadge: "Impacto Vial",
    tipoSlug: "impacto-vial",
    tipoPdf: "impacto-vial",

    getPdfItem: (item) => ({
      liquidacion_general: item.liquidacion_general as never,
      liquidacion_especifica: item.liquidacion_especifica as never,
      liquidacion_tipo: item.liquidacion_tipo as never,
    }),

    buildEditFormModal: ({ item, open, onOpenChange, onSuccess }) => (
      <LiquidacionImpactoVialFormModal
        mode="edit"
        item={item}
        open={open}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
      />
    ),

    buildDetalleModal: ({ item, open, onOpenChange, publicId }) => (
      <LiquidacionDetalleModal
        open={open}
        onOpenChange={onOpenChange}
        kindBadge="Impacto Vial"
        publicId={publicId}
        estado={item.liquidacion_general.estado}
        kindIcon={Move3d}
      >
        {composeDetalleSections({
          lg: item.liquidacion_general,
          lt: item.liquidacion_tipo,
          tipoSection: (
            <LiquidacionDetalleImpactoVialSection
              liquidacionTipo={item.liquidacion_tipo}
            />
          ),
        })}
      </LiquidacionDetalleModal>
    ),
  };

// ── Config: Habilitación Urbana (motor m2) ─────────────────────────

export const HABILITACION_URBANA_CONFIG: LiquidacionCardConfig<LiquidacionHabilitacionUrbanaListItem> =
  {
    domain: "habilitacion-urbana",
    kindIcon: MapIcon,
    kindLabel: "Habilitación Urbana",
    kindBadge: "Habilitación Urbana",
    tipoSlug: "habilitacion-urbana",
    tipoPdf: "habilitacion-urbana",
    showDelegados: true,

    getComprobanteActivo,
    getMunicipalidadLabel,
    getDistritoLabel,
    getEntidadNombre,
    getEntidadDocumento,
    getPdfItem: (item) => ({
      liquidacion_general: item.liquidacion_general as never,
      liquidacion_especifica: item.liquidacion_especifica as never,
      liquidacion_tipo: item.liquidacion_tipo as never,
    }),

    buildCalculoSlot: (item) => {
      const lt = item.liquidacion_tipo;
      return (
        <CalculoM2
          motor="m2"
          areaM2={lt.area_m2}
          costoPorM2={lt.costo_por_m2}
          derechoMinimo={lt.derecho_minimo}
          formatCurrency={fmtCurrency}
        />
      );
    },

    buildDelegadosSlot: (item) => {
      const lg = item.liquidacion_general;
      if (lg.delegados && lg.delegados.length > 0) {
        return <DelegadosListBySpecialty delegados={lg.delegados as never} />;
      }
      return null;
    },

    buildEditFormModal: ({ item, open, onOpenChange, onSuccess }) => (
      <LiquidacionHabilitacionUrbanaFormModal
        mode="edit"
        item={item}
        open={open}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
      />
    ),

    buildDetalleModal: ({ item, open, onOpenChange, publicId }) => (
      <LiquidacionDetalleModal
        open={open}
        onOpenChange={onOpenChange}
        kindBadge="Habilitación Urbana"
        publicId={publicId}
        estado={item.liquidacion_general.estado}
        kindIcon={MapIcon}
      >
        {composeDetalleSections({
          lg: item.liquidacion_general,
          m2: item.liquidacion_tipo,
          tipoSection: (
            <LiquidacionDetalleHabilitacionUrbanaSection
              liquidacionTipo={item.liquidacion_tipo}
            />
          ),
        })}
      </LiquidacionDetalleModal>
    ),
  };

// ── Config: Mecánica de Suelos (motor m2) ───────────────────────────

export const MECANICA_SUELOS_CONFIG: LiquidacionCardConfig<LiquidacionMecanicaSuelosListItem> =
  {
    domain: "mecanica-suelos",
    kindIcon: FlaskRound,
    kindLabel: "Mecánica de Suelos",
    kindBadge: "Mecánica de Suelos",
    tipoSlug: "mecanica-suelos",
    tipoPdf: "mecanica-suelos",
    showDelegados: true,

    getComprobanteActivo,
    getMunicipalidadLabel,
    getDistritoLabel,
    getEntidadNombre,
    getEntidadDocumento,
    getPdfItem: (item) => ({
      liquidacion_general: item.liquidacion_general as never,
      liquidacion_especifica: item.liquidacion_especifica as never,
      liquidacion_tipo: item.liquidacion_tipo as never,
    }),

    buildCalculoSlot: (item) => {
      const lt = item.liquidacion_tipo;
      return (
        <CalculoM2
          motor="m2"
          areaM2={lt.area_m2}
          costoPorM2={lt.costo_por_m2}
          derechoMinimo={lt.derecho_minimo}
          formatCurrency={fmtCurrency}
        />
      );
    },

    buildDelegadosSlot: (item) => {
      const lg = item.liquidacion_general;
      if (lg.delegados && lg.delegados.length > 0) {
        return <DelegadosListBySpecialty delegados={lg.delegados as never} />;
      }
      return null;
    },

    buildEditFormModal: ({ item, open, onOpenChange, onSuccess }) => (
      <LiquidacionMecanicaSuelosFormModal
        mode="edit"
        item={item}
        open={open}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
      />
    ),

    buildDetalleModal: ({ item, open, onOpenChange, publicId }) => (
      <LiquidacionDetalleModal
        open={open}
        onOpenChange={onOpenChange}
        kindBadge="Mecánica de Suelos"
        publicId={publicId}
        estado={item.liquidacion_general.estado}
        kindIcon={FlaskRound}
      >
        {composeDetalleSections({
          lg: item.liquidacion_general,
          m2: item.liquidacion_tipo,
          tipoSection: (
            <LiquidacionDetalleMecanicaSuelosSection
              liquidacionTipo={item.liquidacion_tipo}
            />
          ),
        })}
      </LiquidacionDetalleModal>
    ),
  };

// ── Config: Inspección de Obra (motor visitas, sin delegados) ───────

export const INSPECCION_OBRA_CONFIG: LiquidacionCardConfig<LiquidacionInspeccionObraListItem> =
  {
    domain: "inspeccion-obra",
    kindIcon: ClipboardCheck,
    kindLabel: "Inspección de Obra",
    kindBadge: "Inspección de Obra",
    tipoSlug: "inspeccion-obra",
    tipoPdf: "inspeccion-obra",
    showDelegados: false, // IO usa inspectores, no delegados

    getComprobanteActivo,
    getMunicipalidadLabel,
    getDistritoLabel,
    getEntidadNombre,
    getEntidadDocumento,
    getPdfItem: (item) => ({
      liquidacion_general: item.liquidacion_general as never,
      liquidacion_especifica: item.liquidacion_especifica as never,
      liquidacion_tipo: item.liquidacion_tipo as never,
    }),

    buildCalculoSlot: () => null,
    buildDelegadosSlot: () => null,

    buildEditFormModal: ({ item, open, onOpenChange, onSuccess }) => (
      <LiquidacionInspeccionObraFormModal
        mode="edit"
        item={item}
        open={open}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
      />
    ),

    buildDetalleModal: ({ item, open, onOpenChange, publicId }) => (
      <LiquidacionDetalleModal
        open={open}
        onOpenChange={onOpenChange}
        kindBadge="Inspección de Obra"
        publicId={publicId}
        estado={item.liquidacion_general.estado}
        kindIcon={ClipboardCheck}
      >
        {composeDetalleSections({
          lg: item.liquidacion_general,
          visitas: item.liquidacion_tipo,
          tipoSection: (
            <LiquidacionDetalleInspeccionObraSection
              liquidacionTipo={item.liquidacion_tipo}
            />
          ),
          showDelegados: false,
        })}
      </LiquidacionDetalleModal>
    ),
  };

// ── Hook ────────────────────────────────────────────────────────────

/**
 * useLiquidacionCardState — Centraliza la lógica de las 6 cards de
 * listado (`Liquidacion<Domain>Card`). Cada card pasa a ser:
 *
 * ```tsx
 * export function LiquidacionEdificacionesCard({ item, onUpdated }) {
 *   const { shellProps, modals } = useLiquidacionCardState(
 *     item, EDIFICACIONES_CONFIG, onUpdated,
 *   );
 *   return (<>{<LiquidacionCardShell {...shellProps} />}{modals}</>);
 * }
 * ```
 *
 * El hook:
 *   - Aloja los 5 useState (delegados, detalle, edit, comprobante, delete).
 *   - Deriva `publicId`, `pdfItem`, `handlePrint`, `municipalidadLabel`,
 *     `distritoLabel`, `entidadNombre`, `comprobanteActivo`, `editState.canEdit`.
 *   - Construye `shellProps` con los handlers hacia el shell.
 *   - Renderiza el árbol de modales (Delegados, Detalle, Edit, Comprobante, Delete).
 *
 * Las DIFERENCIAS por dominio se inyectan via `config` (constantes
 * exportadas como `EDIFICACIONES_CONFIG`, `TALUDES_CONFIG`, etc).
 */
export function useLiquidacionCardState<TItem extends LiquidacionCardItemLike>(
  item: TItem,
  config: LiquidacionCardConfig<TItem>,
  onUpdated?: () => void,
): { shellProps: LiquidacionCardShellProps; modals: ReactNode } {
  const lg = item.liquidacion_general;

  const [delegadosModalOpen, setDelegadosModalOpen] = useState(false);
  const [detalleModalOpen, setDetalleModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [comprobanteModalOpen, setComprobanteModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  const publicId = formatPublicId(
    config.tipoSlug,
    lg.fecha_registro,
    item.liquidacion_especifica.numero,
  );

  const editState = canEditLiquidacion(
    lg as Parameters<typeof canEditLiquidacion>[0],
  );

  const pdfItem = config.getPdfItem(item);

  const handlePrint = useCallback(() => {
    void printLiquidacionPreview(
      pdfItem,
      config.tipoPdf,
      buildExtraFieldRows(pdfItem, config.tipoPdf),
    );
  }, [pdfItem, config.tipoPdf]);

  const comprobanteActivo = config.getComprobanteActivo(item);
  const entidadNombre = config.getEntidadNombre(item);

  const shellProps: LiquidacionCardShellProps = {
    kindIcon: config.kindIcon,
    kindLabel: config.kindLabel,
    publicId,
    estado: lg.estado,
    entidadNombre,
    entidadDocumento: config.getEntidadDocumento(item),
    proyectoNombre: lg.denominacion_de_proyecto,
    proyectoUbicacion: config.getDistritoLabel(item),
    municipalidadLabel: config.getMunicipalidadLabel(item),
    distritoLabel: config.getDistritoLabel(item),
    expediente: lg.expediente,
    direccion: lg.proyecto.direccion,
    comprobanteActivo,
    total: lg.total ?? undefined,
    subTotal: lg.sub_total,
    igvMonto:
      lg.total != null && lg.sub_total != null ? lg.total - lg.sub_total : null,
    numeroRevision: lg.numero_revision,
    fechaRegistro: lg.fecha_registro,
    showDelegados: config.showDelegados,
    onDelegados: () => setDelegadosModalOpen(true),
    onPrint: handlePrint,
    canEdit: editState.canEdit,
    onEdit: () => setEditModalOpen(true),
    onDelete: () => setDeleteModalOpen(true),
    onComprobante: () => setComprobanteModalOpen(true),
    onVerDetalle: () => setDetalleModalOpen(true),
    calculoSlot: config.buildCalculoSlot(item),
    delegadosSlot: config.buildDelegadosSlot(item),
  };

  const modals = (
    <>
      {config.showDelegados ? (
        <GestionarDelegadosModal
          open={delegadosModalOpen}
          onOpenChange={setDelegadosModalOpen}
          liquidacionGeneral={
            lg as Parameters<
              typeof GestionarDelegadosModal
            >[0]["liquidacionGeneral"]
          }
        />
      ) : null}

      {config.buildDetalleModal({
        item,
        open: detalleModalOpen,
        onOpenChange: (open) => {
          if (!open) setDetalleModalOpen(false);
        },
        publicId,
      })}

      {config.buildEditFormModal({
        item,
        open: editModalOpen,
        onOpenChange: (open) => {
          if (!open) setEditModalOpen(false);
        },
        onSuccess: () => {
          setEditModalOpen(false);
          onUpdated?.();
        },
      })}

      <ComprobanteFormModal
        open={comprobanteModalOpen}
        onOpenChange={setComprobanteModalOpen}
        liquidacionGeneral={
          lg as Parameters<typeof ComprobanteFormModal>[0]["liquidacionGeneral"]
        }
        onSuccess={() => {
          setComprobanteModalOpen(false);
          onUpdated?.();
        }}
      />

      <EliminarLiquidacionModal
        open={deleteModalOpen}
        onOpenChange={setDeleteModalOpen}
        liquidacion={{ id: lg.id, publicId }}
        entidadNombre={entidadNombre}
        onSuccess={() => {
          setDeleteModalOpen(false);
          onUpdated?.();
        }}
      />
    </>
  );

  return { shellProps, modals };
}
