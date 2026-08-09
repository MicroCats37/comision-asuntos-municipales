"use client";

import type { LiquidacionGeneralListItem } from "../types/liquidacion-general";
import type { LiquidacionInspeccionObraListItem } from "../types/liquidacion-inspeccion-obra.types";
import { LiquidacionGeneralCard } from "./LiquidacionGeneralCard";

interface Props {
  item: LiquidacionInspeccionObraListItem;
  onVerDetalle?: (item: LiquidacionInspeccionObraListItem) => void;
}

export function LiquidacionInspeccionObraCard({ item, onVerDetalle }: Props) {
  return (
    <LiquidacionGeneralCard
      item={item as unknown as LiquidacionGeneralListItem}
      onVerDetalle={
        onVerDetalle as unknown as
          | ((i: LiquidacionGeneralListItem) => void)
          | undefined
      }
    />
  );
}
