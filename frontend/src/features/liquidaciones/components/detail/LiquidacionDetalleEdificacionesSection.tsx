"use client";

import { Building2 } from "lucide-react";
import { formatDecimalPercent } from "@/utils/number-formatter";
import type { PorcentajeObraDatosOut } from "../../schemas/liquidacion-porcentaje.schema";
import { formatCurrency, formatEnumLabel, LabelValue } from "../liquidacion-ui";

interface LiquidacionDetalleEdificacionesSectionProps {
  /** PorcentajeObra data (liquidacion_tipo) */
  liquidacionTipo: PorcentajeObraDatosOut;
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

/**
 * Compact Edificaciones-specific (PorcentajeObra) data for the detail modal.
 * Technical params fused into a single horizontal strip. Tarifa table kept dense.
 * Hides empty trámite block entirely — no reserved space for "—".
 */
export function LiquidacionDetalleEdificacionesSection({
  liquidacionTipo: lt,
}: LiquidacionDetalleEdificacionesSectionProps) {
  const tipoTramite = getTipoTramiteLabel(lt.tipo_tramite);
  const hasTipoTramite =
    lt.tipo_tramite != null && lt.tipo_tramite.trim() !== "";

  return (
    <div className="space-y-3">
      {/* ── Section title ─── */}
      <div className="flex items-center gap-2">
        <Building2 className="h-3.5 w-3.5 text-primary/60" />
        <h3 className="text-xs font-bold text-foreground uppercase tracking-wide">
          Detalle técnico de Edificación
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
