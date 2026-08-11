"use client";

import { useState } from "react";
import {
  Banknote,
  Building2,
  FileText,
  Hash,
  MapPin,
  Pen,
  Scale,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { formatDecimalPercent } from "@/utils/number-formatter";
import { LiquidacionBaseCard } from "./LiquidacionBaseCard";
import { LiquidacionCardHeader, type LiquidacionCardHeaderData } from "../LiquidacionCardHeader";
import { SectionCard, LabelValue, formatCurrency, formatEnumLabel } from "../liquidacion-ui";
import { GestionarDelegadosModal } from "../GestionarDelegadosModal";
import type { LiquidacionEdificacionesListItem } from "../../schemas/liquidacion-edificaciones.schema";

interface LiquidacionEdificacionesCardProps {
  item: LiquidacionEdificacionesListItem;
}

const getTipoTramiteLabel = (value: string | null | undefined): string => {
  switch (value) {
    case "OBRA_NUEVA":
      return "Obra Nueva";
    case "DEMOLICION":
      return "Demolición";
    case "AMPLIACION":
      return "Ampliación";
    case "REMODELACION":
      return "Remodelación";
    case "MODIFICACION_LICENCIA":
      return "Modificación de Licencia";
    case "REINTEGRO":
      return "Reintegro";
    case "PROYECTO_CON_PLANTAS_TIPICAS":
      return "Proyecto con Plantas Típicas";
    default:
      return formatEnumLabel(value);
  }
};

const getTramiteAccionLabel = (value: string | null | undefined): string => {
  switch (value) {
    case "PRIMERA_REVISION":
      return "1ra. Revisión";
    case "REVISION":
      return "Revisión";
    default:
      return formatEnumLabel(value);
  }
};

/**
 * LiquidacionEdificacionesCard — renders an Edificaciones liquidacion
 * using the new composition architecture (LiquidacionBaseCard).
 *
 * Shows Edificaciones-specific data: tipo_tramite, tramite_accion,
 * valor_proyecto, and tariff details per revision.
 */
export function LiquidacionEdificacionesCard({
  item,
}: LiquidacionEdificacionesCardProps) {
  const router = useRouter();
  const [delegadosModalOpen, setDelegadosModalOpen] = useState(false);

  const headerData: LiquidacionCardHeaderData = {
    public_id: item.liquidacion_general.id,
    fecha_registro: item.liquidacion_general.fecha_registro,
    proyectoNombre: item.liquidacion_general.proyecto.denominacion,
    kindBadge: "Edificación",
    expediente: item.liquidacion_general.expediente,
    total: item.liquidacion_general.total,
  };

  const handleVerDetalle = () => {
    router.push(`/liquidaciones/edificaciones/${item.liquidacion_general.id}`);
  };

  const rightSlotActions = (
    <div className="flex items-center gap-2">
      <span
        role="button"
        tabIndex={0}
        onClick={(e) => { e.stopPropagation(); setDelegadosModalOpen(true); }}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.stopPropagation(); setDelegadosModalOpen(true); } }}
        className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg border text-xs font-semibold border-border/60 hover:border-primary/40 hover:bg-primary/5 hover:text-primary cursor-pointer select-none transition-colors"
      >
        <Pen className="h-3 w-3" />
        Delegados
      </span>
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
        {/* ─── Resumen Edificación ─── */}
        <SectionCard icon={<Scale className="h-3.5 w-3.5" />} title="Edificación" className="border-border/60">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <LabelValue label="Tipo de Trámite" value={getTipoTramiteLabel(item.liquidacion_tipo.tipo_tramite)} />
            <LabelValue label="Revisión" value={`N° ${item.liquidacion_general.numero_revision}`} />
            <LabelValue label="Expediente" value={item.liquidacion_general.expediente || "—"} />
          </div>
        </SectionCard>

        {/* ─── Three-column grid: Proyecto + Entidad + Valores ─── */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <SectionCard icon={<Hash className="h-3.5 w-3.5" />} title="Proyecto" className="border-border/60">
            <div className="space-y-2.5">
              <LabelValue label="Nombre" value={item.liquidacion_general.proyecto.denominacion} />
              {item.liquidacion_general.proyecto.direccion && (
                <div className="flex items-start gap-1.5 mt-1 text-xs text-muted-foreground">
                  <MapPin className="h-3 w-3 shrink-0 mt-0.5" />
                  <span className="leading-relaxed">{item.liquidacion_general.proyecto.direccion}</span>
                </div>
              )}
            </div>
          </SectionCard>

          <SectionCard icon={<Building2 className="h-3.5 w-3.5" />} title="Liquidación" className="border-border/60">
            <div className="space-y-2.5">
              <LabelValue label="Valor Declarado" value={formatCurrency(item.liquidacion_tipo.valor_declarado ?? 0)} />
              <LabelValue label="% Liquidación" value={formatDecimalPercent(item.liquidacion_tipo.porcentaje_liquidacion ?? 0)} />
            </div>
          </SectionCard>

          <SectionCard icon={<FileText className="h-3.5 w-3.5" />} title="Valores" className="border-border/60">
            <div className="space-y-2.5">
              <LabelValue label="Subtotal" value={formatCurrency(item.liquidacion_general.sub_total)} />
              <LabelValue label="Total a Pagar" value={formatCurrency(item.liquidacion_general.total)} valueClassName="text-primary font-bold" />
            </div>
          </SectionCard>
        </div>

        {/* ─── Tarifas / Detalles ─── */}
        <div className="grid grid-cols-1 gap-4">
          <SectionCard
            icon={<Scale className="h-3.5 w-3.5" />}
            title={
              <span className="flex items-center gap-1.5">
                Tarifas
                <span className="ml-1 inline-flex items-center justify-center h-4 w-4 rounded-full bg-muted text-[9px] font-bold text-muted-foreground">
                  {item.liquidacion_tipo.detalles?.length ?? 0}
                </span>
              </span>
            }
            className="border-border/60"
          >
            {(item.liquidacion_tipo.detalles?.length ?? 0) > 0 ? (
              <div className="space-y-3">
                {item.liquidacion_tipo.detalles?.map((detalle) => (
                  <div key={detalle.id} className="rounded-lg border border-border/40 bg-muted/20 p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                        Detalle
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <div className="flex flex-col">
                        <span className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider">
                          % Aplicado
                        </span>
                        <span className="text-sm font-bold text-foreground">
                          {formatDecimalPercent(detalle.porcentaje_aplicado)}
                        </span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider">
                          Subt. (S/)
                        </span>
                        <span className="text-sm font-medium text-foreground">
                          {formatCurrency(detalle.subtotal)}
                        </span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider">
                          Total (S/)
                        </span>
                        <span className="text-sm font-medium text-foreground">
                          {formatCurrency(detalle.total)}
                        </span>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      <div className="flex flex-col">
                        <span className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider">
                          IGV (S/)
                        </span>
                        <span className="text-sm font-medium text-foreground">
                          {formatCurrency(detalle.igv)}
                        </span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider">
                          UIT (S/)
                        </span>
                        <span className="text-sm font-medium text-foreground">
                          {formatCurrency(detalle.uit)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground/60 italic">Sin tarifas registradas</p>
            )}
          </SectionCard>
        </div>

        {/* ─── Totales ─── */}
        <SectionCard icon={<Banknote className="h-3.5 w-3.5" />} title="Totales" className="border-border/60">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <LabelValue label="Subtotal" value={formatCurrency(item.liquidacion_general.sub_total)} />
            <LabelValue label="Total" value={formatCurrency(item.liquidacion_general.total)} />
            <div className="flex flex-col bg-primary/5 border border-primary/10 rounded-lg px-3 py-2 -my-0.5">
              <span className="text-[9px] font-bold text-primary uppercase tracking-wider mb-0.5">Total a Pagar</span>
              <span className="text-base font-black text-primary">{formatCurrency(item.liquidacion_general.total)}</span>
            </div>
          </div>
        </SectionCard>

      </LiquidacionBaseCard>

      <GestionarDelegadosModal
        open={delegadosModalOpen}
        onOpenChange={setDelegadosModalOpen}
        liquidacionId={item.liquidacion_general.id}
        municipalidadId={item.liquidacion_general.municipalidad_id}
        tipoLiquidacion="edificacion"
        revisionIds={[]}
        delegadosActuales={[]}
      />
    </>
  );
}
