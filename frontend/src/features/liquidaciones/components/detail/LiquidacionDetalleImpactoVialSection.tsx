"use client";

import { Move3d } from "lucide-react";
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
            value={formatDecimalPercent(lt.porcentaje_liquidacion)}
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
            value={formatDecimalPercent(lt.porcentaje_minimo_uit)}
            valueClassName="text-xs"
          />
        </div>
      </div>
    </div>
  );
}
