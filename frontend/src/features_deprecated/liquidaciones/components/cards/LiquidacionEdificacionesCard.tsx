"use client";

import { useState } from "react";
import {
  AlertCircle,
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
import type { LiquidacionEdificacionesListItem } from "../../types/liquidacion-edificaciones";

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
    public_id: item.public_id,
    fecha_registro: item.fecha_registro,
    proyectoNombre: item.proyecto.nombre,
    kindBadge: "Edificación",
    expediente: item.expediente,
    total: item.total_a_pagar,
  };

  const handleVerDetalle = () => {
    router.push(`/liquidaciones/edificaciones/${item.public_id}`);
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
            <LabelValue label="Tipo de Trámite" value={getTipoTramiteLabel(item.tipo_tramite)} />
            <LabelValue label="Acción" value={getTramiteAccionLabel(item.tramite_accion)} />
            <LabelValue label="Revisión" value={`N° ${item.numero_revision}`} />
            <LabelValue label="Expediente" value={item.expediente || "—"} />
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

          <SectionCard icon={<Building2 className="h-3.5 w-3.5" />} title="Liquidación" className="border-border/60">
            <div className="space-y-2.5">
              <LabelValue label="Valor Declarado" value={formatCurrency(item.valor_declarado)} />
              <LabelValue label="% Liquidación" value={formatDecimalPercent(item.porcentaje_liquidacion)} />
            </div>
          </SectionCard>

          <SectionCard icon={<FileText className="h-3.5 w-3.5" />} title="Valores" className="border-border/60">
            <div className="space-y-2.5">
              <LabelValue label="Subtotal" value={formatCurrency(item.valores.subtotal)} />
              <LabelValue label="Total a Pagar" value={formatCurrency(item.valores.total_a_pagar)} valueClassName="text-primary font-bold" />
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
                  {item.revisiones[0]?.tarifa?.detalles?.length ?? 0}
                </span>
              </span>
            }
            className="border-border/60"
          >
            {(item.revisiones[0]?.tarifa?.detalles?.length ?? 0) > 0 ? (
              <div className="space-y-3">
                {item.revisiones[0].tarifa.detalles.map((detalle: typeof item.revisiones[0]['tarifa']['detalles'][0]) => (
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
            <LabelValue label="Subtotal" value={formatCurrency(item.valores.subtotal)} />
            <LabelValue label="Total" value={formatCurrency(item.valores.total)} />
            <div className="flex flex-col bg-primary/5 border border-primary/10 rounded-lg px-3 py-2 -my-0.5">
              <span className="text-[9px] font-bold text-primary uppercase tracking-wider mb-0.5">Total a Pagar</span>
              <span className="text-base font-black text-primary">{formatCurrency(item.valores.total_a_pagar)}</span>
            </div>
          </div>
        </SectionCard>

        {/* ─── Observación ─── */}
        {item.observacion && (
          <div className="flex items-start gap-3 p-3 rounded-xl bg-amber-500/5 border border-amber-500/15">
            <AlertCircle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider">Observación</span>
              <p className="text-sm text-amber-700/90 font-medium leading-relaxed mt-0.5">{item.observacion}</p>
            </div>
          </div>
        )}
      </LiquidacionBaseCard>

      <GestionarDelegadosModal
        open={delegadosModalOpen}
        onOpenChange={setDelegadosModalOpen}
        liquidacionId={item.public_id}
        municipalidadId={item.municipalidad.id}
        tipoLiquidacion="edificacion"
        revisionIds={item.revisiones.map(r => r.id)}
        delegadosActuales={[]}
      />
    </>
  );
}
