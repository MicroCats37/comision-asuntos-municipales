"use client";

import type { LiquidacionTaludesListItem } from "../types/liquidacion-taludes.types";
import { LiquidacionGeneralCard } from "./LiquidacionGeneralCard";
import type { LiquidacionGeneralListItem } from "../types/liquidacion-general";

interface Props {
  item: LiquidacionTaludesListItem;
  onVerDetalle?: (item: LiquidacionTaludesListItem) => void;
}

export function LiquidacionTaludesCard({ item, onVerDetalle }: Props) {
  return (
    <LiquidacionGeneralCard
      item={item as unknown as LiquidacionGeneralListItem}
      onVerDetalle={onVerDetalle as unknown as ((i: LiquidacionGeneralListItem) => void) | undefined}
    />
  );
}
