"use client";

import {
  FileDown,
  FilePenLine,
  Receipt,
  Trash2,
  Triangle,
  Users,
} from "lucide-react";
import { useState } from "react";
import { formatDecimalPercent } from "@/utils/number-formatter";
import type { PdfLiquidacionItem } from "../../pdf/buildLiquidacionPdfElement";
import { printLiquidacionPreview } from "../../pdf/LiquidacionPdfPreview";
import { buildExtraFieldRows } from "../../pdf/liquidacionPdfHelpers";
import type { LiquidacionTaludesListItem } from "../../schemas/liquidacion-taludes.schema";
import { canEditLiquidacion } from "../../utils/canEditLiquidacion";
import { formatPublicId } from "../../utils/formatPublicId";
import { DelegadosListBySpecialty } from "../DelegadosSection";
import {
  composeDetalleSections,
  LiquidacionDetalleModal,
  LiquidacionDetalleTaludesSection,
} from "../detail";
import { ComprobanteFormModal } from "../forms/ComprobanteFormModal";
import { EliminarLiquidacionModal } from "../forms/EliminarLiquidacionModal";
import { LiquidacionTaludesFormModal } from "../forms/taludes/LiquidacionTaludesFormModal";
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

interface LiquidacionTaludesCardProps {
  item: LiquidacionTaludesListItem;
  onUpdated?: () => void;
}

/**
 * LiquidacionTaludesCard — renders a Taludes liquidacion using the shared
 * LiquidacionCardShell (condensed-row layout). No collapsible, no page
 * navigation: "Ver detalle" opens the inline LiquidacionDetalleModal with the
 * Taludes-specific section.
 */
export function LiquidacionTaludesCard({
  item,
  onUpdated,
}: LiquidacionTaludesCardProps) {
  const [delegadosModalOpen, setDelegadosModalOpen] = useState(false);
  const [detalleModalOpen, setDetalleModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [comprobanteModalOpen, setComprobanteModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  const { liquidacion_general: lg, liquidacion_tipo: lt } = item;
  const proyecto = lg.proyecto;
  const entidad = proyecto.entidad ?? null;

  const publicId = formatPublicId(
    "taludes",
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
      "taludes",
      buildExtraFieldRows(pdfItem, "taludes"),
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
        kindIcon={Triangle}
        kindLabel="Taludes"
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
        kindBadge="Taludes"
        publicId={publicId}
        estado={lg.estado}
        kindIcon={Triangle}
      >
        {composeDetalleSections({
          lg,
          lt,
          tipoSection: (
            <LiquidacionDetalleTaludesSection liquidacionTipo={lt} />
          ),
        })}
      </LiquidacionDetalleModal>

      <LiquidacionTaludesFormModal
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
