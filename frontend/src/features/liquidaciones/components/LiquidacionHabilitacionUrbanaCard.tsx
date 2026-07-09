"use client";

import type { LiquidacionHabilitacionUrbanaListItem } from "../types/liquidacion-habilitacion-urbana.types";
import { LiquidacionGeneralCard } from "./LiquidacionGeneralCard";
import type { LiquidacionGeneralListItem } from "../types/liquidacion-general";

interface Props {
  item: LiquidacionHabilitacionUrbanaListItem;
  onVerDetalle?: (item: LiquidacionHabilitacionUrbanaListItem) => void;
}

export function LiquidacionHabilitacionUrbanaCard({ item, onVerDetalle }: Props) {
  return (
    <LiquidacionGeneralCard
      item={item as unknown as LiquidacionGeneralListItem}
      onVerDetalle={onVerDetalle as unknown as ((i: LiquidacionGeneralListItem) => void) | undefined}
    />
  );
}
