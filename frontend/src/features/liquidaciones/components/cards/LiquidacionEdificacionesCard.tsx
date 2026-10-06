"use client";

import {
  Building2,
  FileDown,
  FilePenLine,
  Receipt,
  Trash2,
  Users,
} from "lucide-react";
import { useState } from "react";
import { formatDecimalPercent } from "@/utils/number-formatter";
import type { PdfLiquidacionItem } from "../../pdf/buildLiquidacionPdfElement";
import { printLiquidacionPreview } from "../../pdf/LiquidacionPdfPreview";
import { buildExtraFieldRows } from "../../pdf/liquidacionPdfHelpers";
import type { LiquidacionEdificacionesListItem } from "../../schemas/liquidacion-edificaciones.schema";
import { canEditLiquidacion } from "../../utils/canEditLiquidacion";
import { formatPublicId } from "../../utils/formatPublicId";
import { DelegadosListBySpecialty } from "../DelegadosSection";
import {
  composeDetalleSections,
  LiquidacionDetalleEdificacionesSection,
  LiquidacionDetalleModal,
} from "../detail";
import { ComprobanteFormModal } from "../forms/ComprobanteFormModal";
import { EliminarLiquidacionModal } from "../forms/EliminarLiquidacionModal";
import { LiquidacionEdificacionFormModal } from "../forms/edificacion/LiquidacionEdificacionFormModal";
import { GestionarDelegadosModal } from "../GestionarDelegadosModal";
import {
  type CardActionItem,
  formatCurrency,
  LiquidacionCardAction,
} from "../liquidacion-ui";
import { CalculoPorcentaje } from "./CalculoDetail";
import { LiquidacionCardShell } from "./LiquidacionCardShell";

const fmtCurrency = (v: number | null | undefined): string =>
  formatCurrency(v ?? 0);

interface LiquidacionEdificacionesCardProps {
  item: LiquidacionEdificacionesListItem;
  onUpdated?: () => void;
}

/**
 * LiquidacionEdificacionesCard — Card condensada tipo row para Edificaciones.
 *
 * Consumes the shared LiquidacionCardShell (canonical condensed-row layout)
 * with the Edificaciones config. Rendered output is 1:1 with the previous
 * standalone condensed card: identity/main/meta/total rows, Delegados section,
 * and shared action set all live in the shell.
 */
export function LiquidacionEdificacionesCard({
  item,
  onUpdated,
}: LiquidacionEdificacionesCardProps) {
  const [delegadosModalOpen, setDelegadosModalOpen] = useState(false);
  const [detalleModalOpen, setDetalleModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [comprobanteModalOpen, setComprobanteModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  const lg = item.liquidacion_general;
  const lt = item.liquidacion_tipo;
  const proyecto = lg.proyecto;
  const entidad = proyecto.entidad ?? null;
  const editState = canEditLiquidacion(lg);

  const publicId = formatPublicId(
    "edificacion",
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
      "edificacion",
      buildExtraFieldRows(pdfItem, "edificacion"),
    );
  };

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

  const comprobanteActivo = lg.comprobantes?.find((c) => c.activo) ?? null;

  const menuItems: CardActionItem[] = [
    {
      icon: <Users className="h-3 w-3" />,
      label: "Delegados",
      onAction: () => setDelegadosModalOpen(true),
    },
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
        kindIcon={Building2}
        kindLabel="Edificaciones"
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
        calculoSlot={
          <CalculoPorcentaje
            motor="porcentaje"
            valorDeclarado={lt.valor_declarado}
            porcentajeLiquidacion={lt.porcentaje_liquidacion}
            derechoMinimo={lt.derecho_minimo}
            especialidades={lt.detalles
              ?.map((d) => d.especialidad?.nombre)
              .filter((n): n is string => Boolean(n))}
            formatCurrency={fmtCurrency}
            formatDecimalPercent={formatDecimalPercent}
          />
        }
        onPrint={handlePrint}
        menuItems={menuItems}
        primaryAction={
          <LiquidacionCardAction
            variant="primary"
            label="Ver detalle"
            onAction={() => setDetalleModalOpen(true)}
          />
        }
        delegadosSlot={
          lg.delegados && lg.delegados.length > 0 ? (
            <DelegadosListBySpecialty delegados={lg.delegados} />
          ) : undefined
        }
      />

      <GestionarDelegadosModal
        open={delegadosModalOpen}
        onOpenChange={setDelegadosModalOpen}
        liquidacionGeneral={lg}
      />

      <LiquidacionDetalleModal
        open={detalleModalOpen}
        onOpenChange={setDetalleModalOpen}
        kindBadge="Edificación"
        publicId={publicId}
        estado={lg.estado}
        kindIcon={Building2}
      >
        {composeDetalleSections({
          lg,
          lt,
          tipoSection: (
            <LiquidacionDetalleEdificacionesSection liquidacionTipo={lt} />
          ),
        })}
      </LiquidacionDetalleModal>

      <LiquidacionEdificacionFormModal
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
