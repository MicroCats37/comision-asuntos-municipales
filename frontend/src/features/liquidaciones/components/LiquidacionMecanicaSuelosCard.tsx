"use client";

import { Grid3X3 } from "lucide-react";
import type { LiquidacionCardBase } from "../types/liquidacion-general";
import type { LiquidacionMecanicaSuelosListItem } from "../types/liquidacion-mecanica-suelos.types";
import { LiquidacionGeneralCard } from "./LiquidacionGeneralCard";

interface Props {
  item: LiquidacionMecanicaSuelosListItem;
  onVerDetalle?: (item: LiquidacionCardBase) => void;
}

/**
 * Detail block for Mecánica de Suelos — area-based calculation.
 * Renders tariff data from revisiones[n].tarifa.
 */
function M2AreaSummary({
  item,
}: {
  item: LiquidacionMecanicaSuelosListItem;
}) {
  const formatCurrency = (value: number | null | undefined) =>
    value != null ? `S/ ${value.toFixed(2)}` : "—";

  // Get tariff data from the first revision
  const firstTarifa = item.revisiones[0]?.tarifa;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
          Modalidad
        </span>
        <span className="text-sm font-medium text-foreground flex items-center gap-1.5">
          <Grid3X3 className="h-3.5 w-3.5 text-primary" />
          Cálculo por área
        </span>
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
          Costo (S/ m²)
        </span>
        <span className="text-sm font-medium text-foreground">
          {formatCurrency(firstTarifa?.costo_por_m2 ?? null)}
        </span>
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
          Derecho Mín.
        </span>
        <span className="text-sm font-medium text-foreground">
          {formatCurrency(firstTarifa?.derecho_minimo ?? null)}
        </span>
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
          Derecho Máx.
        </span>
        <span className="text-sm font-medium text-foreground">
          {formatCurrency(firstTarifa?.derecho_maximo ?? null)}
        </span>
      </div>
    </div>
  );
}

export function LiquidacionMecanicaSuelosCard({ item, onVerDetalle }: Props) {
  return (
    <LiquidacionGeneralCard
      item={item}
      onVerDetalle={onVerDetalle}
      typeSpecificSummary={<M2AreaSummary item={item} />}
    />
  );
}
