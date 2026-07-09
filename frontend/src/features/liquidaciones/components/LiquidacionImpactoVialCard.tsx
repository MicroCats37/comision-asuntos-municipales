"use client";

import type { LiquidacionImpactoVialListItem } from "../types/liquidacion-impacto-vial.types";
import { LiquidacionGeneralCard } from "./LiquidacionGeneralCard";
import type { LiquidacionGeneralListItem } from "../types/liquidacion-general";

interface Props {
  item: LiquidacionImpactoVialListItem;
  onVerDetalle?: (item: LiquidacionImpactoVialListItem) => void;
}

export function LiquidacionImpactoVialCard({ item, onVerDetalle }: Props) {
  return (
    <LiquidacionGeneralCard
      item={item as unknown as LiquidacionGeneralListItem}
      onVerDetalle={onVerDetalle as unknown as ((i: LiquidacionGeneralListItem) => void) | undefined}
    />
  );
}
