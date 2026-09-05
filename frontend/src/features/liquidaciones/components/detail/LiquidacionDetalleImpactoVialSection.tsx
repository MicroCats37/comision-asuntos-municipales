"use client";

import { Move3d, Scale } from "lucide-react";
import { formatDecimalPercent } from "@/utils/number-formatter";
import type { PorcentajeObraDatosOut } from "../../schemas/liquidacion-porcentaje.schema";
import { formatCurrency, formatEnumLabel, LabelValue } from "../liquidacion-ui";

interface LiquidacionDetalleImpactoVialSectionProps {
  /** PorcentajeObra data (liquidacion_tipo) */
  liquidacionTipo: PorcentajeObraDatosOut;
}

/**
 * Compact Impacto Vial-specific (PorcentajeObra) data for the detail modal.
 * Mirrors LiquidacionDetalleEdificacionesSection layout for consistency.
 * Shows tipo tramite (optional) + Liquidación params, then tarifas table.
 */
export function LiquidacionDetalleImpactoVialSection({
  liquidacionTipo: lt,
}: LiquidacionDetalleImpactoVialSectionProps) {
  const tipoTramite = formatEnumLabel(lt.tipo_tramite);
  const hasTipoTramite =
    lt.tipo_tramite != null && lt.tipo_tramite.trim() !== "";

  return (
    <div className="space-y-3">
      {/* ── Section title ─── */}
      <div className="flex items-center gap-2">
        <Move3d className="h-3.5 w-3.5 text-primary/60" />
        <h3 className="text-xs font-bold text-foreground uppercase tracking-wide">
          Detalle técnico de Impacto Vial
        </h3>
        <div className="flex-1 h-px bg-border/40" />
      </div>

      {/* ── Params strip: tipo trámite (optional) + Liquidación params ─── */}
      <div className="flex flex-wrap items-start gap-3 min-w-0">
        {/* Tipo trámite — only render if present */}
        {hasTipoTramite && (
          <div className="flex items-center gap-1.5 rounded-lg border border-border/50 bg-card px-3 py-2">
            <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
              Tipo
            </span>
            <span className="text-xs font-medium text-foreground">
              {tipoTramite}
            </span>
          </div>
        )}

        {/* Liquidación params — always shown */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 rounded-lg border border-border/50 bg-card px-3 py-2">
          <LabelValue
            label="Valor Declarado"
            value={formatCurrency(lt.valor_declarado ?? 0)}
            valueClassName="text-xs"
          />
          <LabelValue
            label="% Liq."
            value={formatDecimalPercent(lt.porcentaje_liquidacion ?? 0)}
            valueClassName="text-xs"
          />
          {lt.derecho_minimo != null && (
            <LabelValue
              label="Der. Mín."
              value={formatCurrency(lt.derecho_minimo)}
              valueClassName="text-xs"
            />
          )}
          {lt.derecho_maximo != null && (
            <LabelValue
              label="Der. Máx."
              value={formatCurrency(lt.derecho_maximo)}
              valueClassName="text-xs"
            />
          )}
          <LabelValue
            label="% Mín. UIT"
            value={formatDecimalPercent(lt.porcentaje_minimo_uit ?? 0)}
            valueClassName="text-xs"
          />
        </div>
      </div>

      {/* ── Tarifas table — compact ─── */}
      <div className="rounded-lg border border-border/50 bg-card overflow-hidden">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-border/40 bg-muted/20">
          <Scale className="h-3 w-3 text-muted-foreground/70" />
          <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
            Tarifas aplicadas
          </h4>
          <span className="ml-1 inline-flex items-center justify-center h-3.5 w-3.5 rounded-full bg-muted text-[9px] font-bold text-muted-foreground">
            {lt.detalles?.length ?? 0}
          </span>
        </div>
        {(lt.detalles?.length ?? 0) > 0 ? (
          <div className="divide-y divide-border/20">
            {/* Table header */}
            <div className="grid grid-cols-[1fr_auto_auto] gap-x-4 px-3 py-1.5 bg-muted/15 min-w-0">
              <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider">
                Descripción
              </span>
              <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider text-right min-w-[4rem]">
                % Aplicado
              </span>
              <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider text-right min-w-[5rem]">
                Subtotal
              </span>
            </div>
            {/* Table rows */}
            {lt.detalles?.map((detalle) => (
              <div
                key={detalle.id}
                className="grid grid-cols-[1fr_auto_auto] gap-x-4 px-3 py-2 hover:bg-muted/8 transition-colors min-w-0"
              >
                <span className="text-xs text-foreground truncate">
                  {detalle.especialidad?.nombre ?? "Tarifa"}
                </span>
                <span className="text-xs font-semibold text-primary text-right min-w-[4rem]">
                  {formatDecimalPercent(detalle.porcentaje_aplicado)}
                </span>
                <span className="text-xs font-semibold text-foreground text-right min-w-[5rem]">
                  {formatCurrency(detalle.subtotal)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="px-3 py-2 text-xs text-muted-foreground/60 italic">
            Sin tarifas registradas
          </p>
        )}
      </div>
    </div>
  );
}
