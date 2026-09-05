"use client";

import { Building2, FileDown, FilePenLine, Receipt, Users } from "lucide-react";
import { useState } from "react";
import type { PdfLiquidacionItem } from "../../pdf/buildLiquidacionPdfElement";
import { printLiquidacion } from "../../pdf/printLiquidacion";
import type { LiquidacionEdificacionesListItem } from "../../schemas/liquidacion-edificaciones.schema";
import { canEditLiquidacion } from "../../utils/canEditLiquidacion";
import { formatPublicId } from "../../utils/formatPublicId";
import {
  LiquidacionDetalleEdificacionesSection,
  LiquidacionDetalleGeneralSection,
  LiquidacionDetalleModal,
} from "../detail";
import { ComprobanteFormModal } from "../forms/ComprobanteFormModal";
import { EdificacionesEditFormModal } from "../forms/EdificacionesEditFormModal";
import { GestionarDelegadosModal } from "../GestionarDelegadosModal";
import { DelegadosListBySpecialty } from "../DelegadosSection";
import {
  CardActionItem,
  CardActionsMenu,
  LiquidacionCardAction,
  formatCurrency,
} from "../liquidacion-ui";
import { LiquidacionCardShell } from "./LiquidacionCardShell";

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

  const lg = item.liquidacion_general;
  const lt = item.liquidacion_tipo;
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
    printLiquidacion(pdfItem, "edificacion");
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

  const comprobanteActivo =
    lg.comprobantes?.find((c) => c.activo) ?? null;

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
        ]
      : []),
    {
      icon: <Receipt className="h-3 w-3" />,
      label: comprobanteActivo ? "Reemplazar comprobante" : "Agregar comprobante",
      onAction: () => setComprobanteModalOpen(true),
    },
  ];

  return (
    <>
      <LiquidacionCardShell
        kindIcon={Building2}
        publicId={publicId}
        estado={lg.estado}
        entidadNombre={entidadNombre}
        proyectoNombre={lg.denominacion_de_proyecto}
        municipalidadLabel={municipalidadLabel}
        distritoLabel={distritoLabel}
        expediente={lg.expediente}
        codigoCta={lg.codigo_cta}
        legacy={lg.legacy}
        comprobanteActivo={comprobanteActivo}
        total={lg.total}
        subTotal={lg.sub_total}
        fechaRegistro={lg.fecha_registro}
        valuesSlot={
          <div className="flex items-center gap-6">
            <div>
              <p className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider leading-none mb-0.5">
                Subtotal
              </p>
              <p className="text-sm font-black text-foreground leading-none">
                {lg.sub_total != null ? formatCurrency(lg.sub_total) : "—"}
              </p>
            </div>
            <div>
              <p className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider leading-none mb-0.5">
                Total
              </p>
              <p className="text-sm font-black text-foreground leading-none">
                {formatCurrency(lg.total ?? 0)}
              </p>
            </div>
          </div>
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
        kindBadge="Edificación"
        publicId={publicId}
        estado={lg.estado}
        kindIcon={Building2}
        total={lg.total}
        generalSection={
          <LiquidacionDetalleGeneralSection liquidacionGeneral={lg} />
        }
        especificoSection={
          <LiquidacionDetalleEdificacionesSection liquidacionTipo={lt} />
        }
      />

      <EdificacionesEditFormModal
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
    </>
  );
}
