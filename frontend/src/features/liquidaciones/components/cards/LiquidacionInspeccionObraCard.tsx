"use client";

import {
  ClipboardCheck,
  FileDown,
  FilePenLine,
  Receipt,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import type { PdfLiquidacionItem } from "../../pdf/buildLiquidacionPdfElement";
import { printLiquidacionPreview } from "../../pdf/LiquidacionPdfPreview";
import { buildExtraFieldRows } from "../../pdf/liquidacionPdfHelpers";
import type { LiquidacionInspeccionObraListItem } from "../../schemas/liquidacion-inspeccion-obra.schema";
import { canEditLiquidacion } from "../../utils/canEditLiquidacion";
import { formatPublicId } from "../../utils/formatPublicId";
import {
  composeDetalleSections,
  LiquidacionDetalleInspeccionObraSection,
  LiquidacionDetalleModal,
} from "../detail";
import { ComprobanteFormModal } from "../forms/ComprobanteFormModal";
import { EliminarLiquidacionModal } from "../forms/EliminarLiquidacionModal";
import { LiquidacionInspeccionObraFormModal } from "../forms/inspeccion-obra/LiquidacionInspeccionObraFormModal";
import {
  type CardActionItem,
  formatCurrency,
  LiquidacionCardAction,
} from "../liquidacion-ui";
import { CalculoVisitas } from "./CalculoDetail";
import { LiquidacionCardShell } from "./LiquidacionCardShell";

const fmtCurrency = (v: number | null | undefined): string =>
  formatCurrency(v ?? 0);

interface LiquidacionInspeccionObraCardProps {
  item: LiquidacionInspeccionObraListItem;
  onUpdated?: () => void;
}

/**
 * LiquidacionInspeccionObraCard — renders an Inspección de Obra liquidacion
 * using the shared LiquidacionCardShell (condensed-row layout). No collapsible,
 * no page navigation: "Ver detalle" opens the inline LiquidacionDetalleModal
 * with the IO-specific section.
 *
 * Uses Inspectores (NOT Delegados) — the Delegados action is omitted
 * (showDelegados=false), preserving its distinct domain design.
 */
export function LiquidacionInspeccionObraCard({
  item,
  onUpdated,
}: LiquidacionInspeccionObraCardProps) {
  const [detalleModalOpen, setDetalleModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [comprobanteModalOpen, setComprobanteModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  const { liquidacion_general: lg, liquidacion_tipo: lt } = item;
  const proyecto = lg.proyecto;
  const entidad = proyecto.entidad ?? null;

  const publicId = formatPublicId(
    "inspeccion-obra",
    lg.fecha_registro,
    item.liquidacion_especifica.numero,
  );

  const pdfItem: PdfLiquidacionItem = {
    liquidacion_general: lg as PdfLiquidacionItem["liquidacion_general"],
    liquidacion_especifica:
      item.liquidacion_especifica as PdfLiquidacionItem["liquidacion_especifica"],
    liquidacion_tipo: lt as PdfLiquidacionItem["liquidacion_tipo"],
  };

  const handlePrint = () => {
    void printLiquidacionPreview(
      pdfItem,
      "inspeccion-obra",
      buildExtraFieldRows(pdfItem, "inspeccion-obra"),
    );
  };

  const editState = canEditLiquidacion(lg);
  const comprobanteActivo = lg.comprobantes?.find((c) => c.activo) ?? null;

  const municipalidadLabel = lg.municipalidad
    ? lg.municipalidad.codigo
      ? `${lg.municipalidad.codigo} - ${lg.municipalidad.nombre}`
      : lg.municipalidad.nombre
    : "—";

  const distritoLabel = lg.proyecto.distrito
    ? [
        lg.proyecto.distrito.nombre,
        lg.proyecto.distrito.provincia?.nombre,
        lg.proyecto.distrito.departamento?.nombre,
      ]
        .filter(Boolean)
        .join(" - ")
    : "—";

  const entidadNombre =
    lg.proyecto.entidad?.razon_social ?? lg.proyecto.nombre_propietario ?? "—";

  const menuItems: CardActionItem[] = [
    // No Delegados — InspeccionObra uses showDelegados=false (Inspectores domain)
    {
      icon: <FileDown className="h-3 w-3" />,
      label: "PDF",
      onAction: handlePrint,
    },
    ...(editState.canEdit
      ? [
          {
            icon: <FilePenLine className="h-3 w-3" />,
            label: "Editar",
            onAction: () => setEditModalOpen(true),
          },
          {
            icon: <Trash2 className="h-3 w-3" />,
            label: "Eliminar",
            onAction: () => setDeleteModalOpen(true),
          },
        ]
      : []),
    {
      icon: <Receipt className="h-3 w-3" />,
      label: comprobanteActivo
        ? "Reemplazar comprobante"
        : "Agregar comprobante",
      onAction: () => setComprobanteModalOpen(true),
    },
  ];

  return (
    <>
      <LiquidacionCardShell
        kindIcon={ClipboardCheck}
        kindLabel="Inspección de Obra"
        publicId={publicId}
        estado={lg.estado}
        entidadNombre={entidadNombre}
        entidadDocumento={entidad?.numero_documento ?? undefined}
        proyectoNombre={lg.denominacion_de_proyecto}
        proyectoUbicacion={distritoLabel}
        municipalidadLabel={municipalidadLabel}
        distritoLabel={distritoLabel}
        expediente={lg.expediente}
        direccion={proyecto.direccion}
        comprobanteActivo={comprobanteActivo}
        total={lg.total}
        subTotal={lg.sub_total}
        igvMonto={
          lg.total != null && lg.sub_total != null
            ? lg.total - lg.sub_total
            : null
        }
        numeroRevision={lg.numero_revision}
        fechaRegistro={lg.fecha_registro}
        menuItems={menuItems}
        primaryAction={
          <LiquidacionCardAction
            variant="primary"
            label="Ver detalle"
            onAction={() => setDetalleModalOpen(true)}
          />
        }
        delegadosSlot={
          <span className="flex items-center gap-2 text-xs text-muted-foreground/70">
            {(() => {
              const registros = lt.registros_pago ?? [];
              if (registros.length === 0) {
                return (
                  <span className="italic text-muted-foreground/50">
                    Sin pagos registrados
                  </span>
                );
              }
              const totalPagadas = registros.reduce(
                (sum, r) => sum + (r.inspecciones_pagadas ?? 0),
                0,
              );
              const latest = [...registros].sort((a, b) => {
                const dateA = a.fecha_registro
                  ? new Date(a.fecha_registro).getTime()
                  : 0;
                const dateB = b.fecha_registro
                  ? new Date(b.fecha_registro).getTime()
                  : 0;
                return dateB - dateA;
              })[0];
              const MESES = [
                "ene",
                "feb",
                "mar",
                "abr",
                "may",
                "jun",
                "jul",
                "ago",
                "sep",
                "oct",
                "nov",
                "dic",
              ];
              const mesLabel = latest.mes ? MESES[latest.mes - 1] : null;
              const periodoLabel = latest.periodo ?? null;
              const latestLabel =
                mesLabel && periodoLabel
                  ? `${mesLabel} ${periodoLabel}`
                  : mesLabel
                    ? mesLabel
                    : periodoLabel
                      ? String(periodoLabel)
                      : null;
              return (
                <>
                  <span className="font-semibold text-foreground">
                    {totalPagadas}
                  </span>
                  <span className="text-muted-foreground/60">
                    inspecciones pagadas
                  </span>
                  {latestLabel && (
                    <>
                      <span className="text-muted-foreground/40">·</span>
                      <span className="text-muted-foreground/60">
                        última: {latestLabel}
                      </span>
                    </>
                  )}
                </>
              );
            })()}
          </span>
        }
      />

      <LiquidacionDetalleModal
        open={detalleModalOpen}
        onOpenChange={setDetalleModalOpen}
        kindBadge="Inspección de Obra"
        publicId={publicId}
        estado={lg.estado}
        kindIcon={ClipboardCheck}
      >
        {composeDetalleSections({
          lg,
          visitas: lt,
          tipoSection: (
            <LiquidacionDetalleInspeccionObraSection liquidacionTipo={lt} />
          ),
          showDelegados: false,
        })}
      </LiquidacionDetalleModal>

      <LiquidacionInspeccionObraFormModal
        mode="edit"
        open={editModalOpen}
        onOpenChange={setEditModalOpen}
        item={item}
        onSuccess={() => {
          setEditModalOpen(false);
          onUpdated?.();
        }}
      />

      <ComprobanteFormModal
        open={comprobanteModalOpen}
        onOpenChange={setComprobanteModalOpen}
        liquidacionGeneral={lg}
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
}
