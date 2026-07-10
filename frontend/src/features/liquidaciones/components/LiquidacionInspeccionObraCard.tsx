"use client";

import { ClipboardCheck } from "lucide-react";
import type { LiquidacionCardBase } from "../types/liquidacion-general";
import type { LiquidacionInspeccionObraListItem } from "../types/liquidacion-inspeccion-obra.types";
import { LiquidacionGeneralCard } from "./LiquidacionGeneralCard";

interface Props {
  item: LiquidacionInspeccionObraListItem;
  onVerDetalle?: (item: LiquidacionCardBase) => void;
}

/**
 * Detail block for Inspección de Obra — visitas-based calculation.
 * Renders tariff data from revisiones[n].tarifa.
 * cantidad_visitas comes from tarifa.cantidad_visitas (populated by backend).
 * derecho comes from valores.total_a_pagar.
 */
function IOVisitasSummary({
  item,
}: {
  item: LiquidacionInspeccionObraListItem;
}) {
  const formatCurrency = (value: number | null | undefined) =>
    value != null ? `S/ ${value.toFixed(2)}` : "—";

  // Get tariff data from the first revision (IO typically has one revision per liquidacion)
  const firstTarifa = item.revisiones[0]?.tarifa;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
          Categoría
        </span>
        <span className="text-sm font-medium text-foreground flex items-center gap-1.5">
          <ClipboardCheck className="h-3.5 w-3.5 text-primary" />
          {firstTarifa?.categoria ?? "—"}
        </span>
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
          Cant. Visitas
        </span>
        <span className="text-sm font-medium text-foreground">
          {firstTarifa?.cantidad_visitas ?? "—"}
        </span>
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
          Costo/Visita
        </span>
        <span className="text-sm font-medium text-foreground">
          {formatCurrency(firstTarifa?.costo_por_visita ?? null)}
        </span>
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
          Derecho
        </span>
        <span className="text-sm font-medium text-foreground">
          {formatCurrency(item.valores.total_a_pagar)}
        </span>
      </div>
    </div>
  );
}

export function LiquidacionInspeccionObraCard({ item, onVerDetalle }: Props) {
  return (
    <LiquidacionGeneralCard
      item={item}
      onVerDetalle={onVerDetalle}
      typeSpecificSummary={<IOVisitasSummary item={item} />}
    />
  );
}
