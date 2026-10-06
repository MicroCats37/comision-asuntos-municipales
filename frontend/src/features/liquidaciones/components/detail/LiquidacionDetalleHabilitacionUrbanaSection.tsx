"use client";

import { Ruler } from "lucide-react";
import type { M2DatosOut } from "../../schemas/liquidacion-m2.schema";
import { formatCurrency, LabelValue } from "../liquidacion-ui";

interface LiquidacionDetalleHabilitacionUrbanaSectionProps {
  /** M2 data (liquidacion_tipo) */
  liquidacionTipo: M2DatosOut;
}

/**
 * Compact Habilitación Urbana-specific (M2) data for the detail modal.
 * Mirrors the compact layout of LiquidacionDetalleEdificacionesSection.
 * Shows area, costo/m², and derecho bounds.
 */
export function LiquidacionDetalleHabilitacionUrbanaSection({
  liquidacionTipo: lt,
}: LiquidacionDetalleHabilitacionUrbanaSectionProps) {
  return (
    <div className="space-y-3">
      {/* ── Section title ─── */}
      <div className="flex items-center gap-2">
        <Ruler className="h-3.5 w-3.5 text-primary/60" />
        <h3 className="text-xs font-bold text-foreground uppercase tracking-wide">
          Detalle técnico de Habilitación Urbana
        </h3>
        <div className="flex-1 h-px bg-border/40" />
      </div>

      {/* ── Params strip: Liquidación M2 params ─── */}
      <div className="flex flex-wrap items-start gap-3 min-w-0">
        {/* Liquidación params — area + costo */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 rounded-lg border border-border/50 bg-card px-3 py-2">
          <LabelValue
            label="Área"
            value={`${lt.area_m2 ?? 0} m²`}
            valueClassName="text-xs"
          />
          <LabelValue
            label="Costo/m²"
            value={formatCurrency(lt.costo_por_m2)}
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
        </div>
      </div>
    </div>
  );
}
