"use client";

import {
  Banknote,
  Building2,
  ClipboardCheck,
  Hash,
  MapPin,
  Scale,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { LiquidacionBaseCard } from "./LiquidacionBaseCard";
import { LiquidacionCardHeader, type LiquidacionCardHeaderData } from "../LiquidacionCardHeader";
import { SectionCard, LabelValue, formatCurrency, formatEnumLabel } from "../liquidacion-ui";
import type { LiquidacionInspeccionObraListItem } from "../../types/liquidacion-inspeccion-obra.types";

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

  const headerData: LiquidacionCardHeaderData = {
    public_id: item.public_id,
    fecha_registro: item.fecha_registro,
    proyectoNombre: item.proyecto.nombre,
    kindBadge: "Inspección de Obra",
    expediente: undefined,
    total: item.valores.total_a_pagar,
  };

  const handleVerDetalle = () => {
    router.push(`/liquidaciones/inspeccion-obra/${item.public_id}`);
  };

  const rightSlotActions = (
    <div className="flex items-center gap-2">
      <span
        role="button"
        tabIndex={0}
        onClick={(e) => { e.stopPropagation(); handleVerDetalle(); }}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.stopPropagation(); handleVerDetalle(); } }}
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
        <SectionCard icon={<ClipboardCheck className="h-3.5 w-3.5" />} title="Inspección de Obra" className="border-border/60">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <LabelValue label="Revisión" value={`N° ${item.numero_revision}`} />
            <LabelValue label="Categoría" value={formatEnumLabel(item.revisiones[0]?.tarifa?.categoria ?? "")} />
            <LabelValue label="Cant. Visitas" value={`${item.revisiones[0]?.tarifa?.cantidad_visitas ?? 0}`} />
          </div>
        </SectionCard>

        {/* ─── Three-column grid: Proyecto + Entidad + Valores ─── */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <SectionCard icon={<Hash className="h-3.5 w-3.5" />} title="Proyecto" className="border-border/60">
            <div className="space-y-2.5">
              <LabelValue label="Nombre" value={item.proyecto.nombre} />
              {item.proyecto.direccion && (
                <div className="flex items-start gap-1.5 mt-1 text-xs text-muted-foreground">
                  <MapPin className="h-3 w-3 shrink-0 mt-0.5" />
                  <span className="leading-relaxed">{item.proyecto.direccion}</span>
                </div>
              )}
            </div>
          </SectionCard>

          <SectionCard icon={<Scale className="h-3.5 w-3.5" />} title="Liquidación" className="border-border/60">
            <div className="space-y-2.5">
              <LabelValue label="Cant. Visitas" value={`${item.revisiones[0]?.tarifa?.cantidad_visitas ?? 0}`} />
            </div>
          </SectionCard>

          <SectionCard icon={<Banknote className="h-3.5 w-3.5" />} title="Valores" className="border-border/60">
            <div className="space-y-2.5">
              <LabelValue label="Subtotal" value={formatCurrency(item.valores.subtotal)} />
              <LabelValue label="Total a Pagar" value={formatCurrency(item.valores.total_a_pagar)} valueClassName="text-primary font-bold" />
            </div>
          </SectionCard>
        </div>

        {/* ─── Totales ─── */}
        <SectionCard icon={<Banknote className="h-3.5 w-3.5" />} title="Totales" className="border-border/60">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <LabelValue label="Subtotal" value={formatCurrency(item.valores.subtotal)} />
            <LabelValue label="Total" value={formatCurrency(item.valores.total)} />
            <div className="flex flex-col bg-primary/5 border border-primary/10 rounded-lg px-3 py-2 -my-0.5">
              <span className="text-[9px] font-bold text-primary uppercase tracking-wider mb-0.5">Total a Pagar</span>
              <span className="text-base font-black text-primary">{formatCurrency(item.valores.total_a_pagar)}</span>
            </div>
          </div>
        </SectionCard>
      </LiquidacionBaseCard>
    </>
  );
}
