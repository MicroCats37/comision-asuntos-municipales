"use client";

import { Grid3X3 } from "lucide-react";
import type { LiquidacionCardBase } from "../types/liquidacion-general";
import type { LiquidacionTaludesListItem } from "../types/liquidacion-taludes.types";
import { LiquidacionGeneralCard } from "./LiquidacionGeneralCard";
import { formatDecimalPercent } from "@/utils/number-formatter";

interface Props {
  item: LiquidacionTaludesListItem;
  onVerDetalle?: (item: LiquidacionCardBase) => void;
}

/**
 * Detail block for Taludes — percentage-of-obra calculation.
 * Renders tariff data from revisiones[n].tarifa using percentage fields.
 */
function PercentageSummary({
  item,
}: {
  item: LiquidacionTaludesListItem;
}) {
  const formatCurrency = (value: number | null | undefined) =>
    value != null ? `S/ ${value.toFixed(2)}` : "—";

  const formatPercent = (value: number | null | undefined) =>
    formatDecimalPercent(value);

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
          % de Obra
        </span>
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
          % Liquidación
        </span>
        <span className="text-sm font-medium text-foreground">
          {formatPercent(firstTarifa?.porcentaje_liquidacion ?? null)}
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
          % UIT Mín.
        </span>
        <span className="text-sm font-medium text-foreground">
          {formatPercent(firstTarifa?.porcentaje_minimo_uit ?? null)}
        </span>
      </div>
    </div>
  );
}

export function LiquidacionTaludesCard({ item, onVerDetalle }: Props) {
  return (
    <LiquidacionGeneralCard
      item={item}
      onVerDetalle={onVerDetalle}
      typeSpecificSummary={<PercentageSummary item={item} />}
    />
  );
}
