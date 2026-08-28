"use client";

import {
  Banknote,
  Building2,
  ClipboardCheck,
  FileDown,
  Hash,
  MapPin,
  Scale,
} from "lucide-react";
import { useRouter } from "next/navigation";
import type { PdfLiquidacionItem } from "../../pdf/buildLiquidacionPdfElement";
import { printLiquidacion } from "../../pdf/printLiquidacion";
import type { LiquidacionInspeccionObraListItem } from "../../schemas/liquidacion-inspeccion-obra.schema";
import { formatPublicId } from "../../utils/formatPublicId";
import {
  LiquidacionCardHeader,
  type LiquidacionCardHeaderData,
} from "../LiquidacionCardHeader";
import {
  formatCurrency,
  formatEnumLabel,
  LabelValue,
  SectionCard,
} from "../liquidacion-ui";
import { LiquidacionBaseCard } from "./LiquidacionBaseCard";

interface LiquidacionInspeccionObraCardProps {
  item: LiquidacionInspeccionObraListItem;
}

/**
 * LiquidacionInspeccionObraCard — renders an Inspección de Obra liquidacion
 * using the new composition architecture (LiquidacionBaseCard).
 *
 * Shows IO-specific data: categoria, cantidad_visitas, porcentaje_uit.
 * Uses Inspectores (NOT Delegados) — distinct from all other domains.
 */
export function LiquidacionInspeccionObraCard({
  item,
}: LiquidacionInspeccionObraCardProps) {
  const router = useRouter();

  const {
    liquidacion_general: lg,
    liquidacion_especifica,
    liquidacion_tipo: lt,
  } = item;

  const headerData: LiquidacionCardHeaderData = {
    public_id: formatPublicId(
      "inspeccion-obra",
      lg.fecha_registro,
      item.liquidacion_especifica.numero,
    ),
    fecha_registro: lg.fecha_registro,
    proyectoNombre: lg.proyecto.denominacion,
    kindBadge: "Inspección de Obra",
    expediente: undefined,
    total: lg.total,
  };

  const handleVerDetalle = () => {
    router.push(`/liquidaciones/inspeccion-obra/${lg.id}`);
  };

  const pdfItem: PdfLiquidacionItem = {
    liquidacion_general: lg as PdfLiquidacionItem["liquidacion_general"],
    liquidacion_especifica:
      item.liquidacion_especifica as PdfLiquidacionItem["liquidacion_especifica"],
    liquidacion_tipo: lt as PdfLiquidacionItem["liquidacion_tipo"],
  };

  const handlePrint = () => {
    printLiquidacion(pdfItem, "inspeccion-obra");
  };

  const rightSlotActions = (
    <div className="flex items-center gap-2">
      <span
        role="button"
        tabIndex={0}
        onClick={(e) => {
          e.stopPropagation();
          handlePrint();
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.stopPropagation();
            handlePrint();
          }
        }}
        className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg border text-xs font-semibold border-border/60 hover:border-primary/40 hover:bg-primary/5 hover:text-primary cursor-pointer select-none transition-colors"
      >
        <FileDown className="h-3 w-3" />
        PDF
      </span>
      <span
        role="button"
        tabIndex={0}
        onClick={(e) => {
          e.stopPropagation();
          handleVerDetalle();
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.stopPropagation();
            handleVerDetalle();
          }
        }}
        className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg border text-xs font-semibold border-primary/30 text-primary hover:bg-primary/10 hover:border-primary/50 cursor-pointer select-none transition-colors"
      >
        Ver detalle
      </span>
    </div>
  );

  return (
    <>
      <LiquidacionBaseCard
        data={headerData}
        rightSlotChildren={rightSlotActions}
      >
        {/* ─── Resumen Inspección de Obra ─── */}
        <SectionCard
          icon={<ClipboardCheck className="h-3.5 w-3.5" />}
          title="Inspección de Obra"
          className="border-border/60"
        >
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <LabelValue label="Revisión" value={`N° ${lg.numero_revision}`} />
            <LabelValue
              label="Categoría"
              value={formatEnumLabel(lt.categoria ?? "")}
            />
            <LabelValue
              label="Cant. Visitas"
              value={`${lt.cantidad_visitas ?? 0}`}
            />
          </div>
        </SectionCard>

        {/* ─── Three-column grid: Proyecto + Entidad + Valores ─── */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <SectionCard
            icon={<Hash className="h-3.5 w-3.5" />}
            title="Proyecto"
            className="border-border/60"
          >
            <div className="space-y-2.5">
              <LabelValue label="Nombre" value={lg.proyecto.denominacion} />
              {lg.proyecto.direccion && (
                <div className="flex items-start gap-1.5 mt-1 text-xs text-muted-foreground">
                  <MapPin className="h-3 w-3 shrink-0 mt-0.5" />
                  <span className="leading-relaxed">
                    {lg.proyecto.direccion}
                  </span>
                </div>
              )}
            </div>
          </SectionCard>

          <SectionCard
            icon={<Scale className="h-3.5 w-3.5" />}
            title="Liquidación"
            className="border-border/60"
          >
            <div className="space-y-2.5">
              <LabelValue
                label="Cant. Visitas"
                value={`${lt.cantidad_visitas ?? 0}`}
              />
              <LabelValue label="% UIT" value={`${lt.porcentaje_uit ?? 0}`} />
            </div>
          </SectionCard>

          <SectionCard
            icon={<Banknote className="h-3.5 w-3.5" />}
            title="Valores"
            className="border-border/60"
          >
            <div className="space-y-2.5">
              <LabelValue
                label="Subtotal"
                value={formatCurrency(lg.sub_total)}
              />
              <LabelValue
                label="Total a Pagar"
                value={formatCurrency(lg.total)}
                valueClassName="text-primary font-bold"
              />
            </div>
          </SectionCard>
        </div>

        {/* ─── Totales ─── */}
        <SectionCard
          icon={<Banknote className="h-3.5 w-3.5" />}
          title="Totales"
          className="border-border/60"
        >
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <LabelValue label="Subtotal" value={formatCurrency(lg.sub_total)} />
            <LabelValue label="Total" value={formatCurrency(lg.total)} />
            <div className="flex flex-col bg-primary/5 border border-primary/10 rounded-lg px-3 py-2 -my-0.5">
              <span className="text-[9px] font-bold text-primary uppercase tracking-wider mb-0.5">
                Total a Pagar
              </span>
              <span className="text-base font-black text-primary">
                {formatCurrency(lg.total)}
              </span>
            </div>
          </div>
        </SectionCard>
      </LiquidacionBaseCard>
    </>
  );
}
