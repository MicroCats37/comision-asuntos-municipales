"use client";

import {
  FileDown,
  FilePenLine,
  Receipt,
  Ruler,
  Trash2,
  Users,
} from "lucide-react";
import { useState } from "react";
import type { PdfLiquidacionItem } from "../../pdf/buildLiquidacionPdfElement";
import { printLiquidacionPreview } from "../../pdf/LiquidacionPdfPreview";
import { buildExtraFieldRows } from "../../pdf/liquidacionPdfHelpers";
import type { LiquidacionHabilitacionUrbanaListItem } from "../../schemas/liquidacion-habilitacion-urbana.schema";
import { canEditLiquidacion } from "../../utils/canEditLiquidacion";
import { formatPublicId } from "../../utils/formatPublicId";
import { DelegadosListBySpecialty } from "../DelegadosSection";
import {
  composeDetalleSections,
  LiquidacionDetalleHabilitacionUrbanaSection,
  LiquidacionDetalleModal,
} from "../detail";
import { ComprobanteFormModal } from "../forms/ComprobanteFormModal";
import { EliminarLiquidacionModal } from "../forms/EliminarLiquidacionModal";
import { LiquidacionHabilitacionUrbanaFormModal } from "../forms/habilitacion-urbana/LiquidacionHabilitacionUrbanaFormModal";
import { GestionarDelegadosModal } from "../GestionarDelegadosModal";
import {
  type CardActionItem,
  formatCurrency,
  LiquidacionCardAction,
} from "../liquidacion-ui";
import { CalculoM2 } from "./CalculoDetail";
import { LiquidacionCardShell } from "./LiquidacionCardShell";

const fmtCurrency = (v: number | null | undefined): string =>
  formatCurrency(v ?? 0);

interface LiquidacionHabilitacionUrbanaCardProps {
  item: LiquidacionHabilitacionUrbanaListItem;
  onUpdated?: () => void;
}

/**
 * LiquidacionHabilitacionUrbanaCard — renders a Habilitación Urbana
 * liquidacion using the shared LiquidacionCardShell (condensed-row layout).
 * No collapsible, no page navigation: "Ver detalle" opens the inline
 * LiquidacionDetalleModal with the HU-specific section.
 */
export function LiquidacionHabilitacionUrbanaCard({
  item,
  onUpdated,
}: LiquidacionHabilitacionUrbanaCardProps) {
  const [delegadosModalOpen, setDelegadosModalOpen] = useState(false);
  const [detalleModalOpen, setDetalleModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [comprobanteModalOpen, setComprobanteModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  const { liquidacion_general: lg, liquidacion_tipo: lt } = item;
  const proyecto = lg.proyecto;
  const entidad = proyecto.entidad ?? null;

  const publicId = formatPublicId(
    "habilitacion-urbana",
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
      "habilitacion-urbana",
      buildExtraFieldRows(pdfItem, "habilitacion-urbana"),
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
        kindIcon={Ruler}
        kindLabel="Habilitación Urbana"
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
          <CalculoM2
            motor="m2"
            areaM2={lt.area_m2}
            costoPorM2={lt.costo_por_m2}
            derechoMinimo={lt.derecho_minimo}
            formatCurrency={fmtCurrency}
          />
        }
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
        kindBadge="Habilitación Urbana"
        publicId={publicId}
        estado={lg.estado}
        kindIcon={Ruler}
      >
        {composeDetalleSections({
          lg,
          m2: lt,
          tipoSection: (
            <LiquidacionDetalleHabilitacionUrbanaSection liquidacionTipo={lt} />
          ),
        })}
      </LiquidacionDetalleModal>

      <LiquidacionHabilitacionUrbanaFormModal
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
