"use client";

import type { LiquidacionMecanicaSuelosListItem } from "../types/liquidacion-mecanica-suelos.types";
import { LiquidacionGeneralCard } from "./LiquidacionGeneralCard";
import type { LiquidacionGeneralListItem } from "../types/liquidacion-general";

interface Props {
  item: LiquidacionMecanicaSuelosListItem;
  onVerDetalle?: (item: LiquidacionMecanicaSuelosListItem) => void;
}

export function LiquidacionMecanicaSuelosCard({ item, onVerDetalle }: Props) {
  return (
    <LiquidacionGeneralCard
      item={item as unknown as LiquidacionGeneralListItem}
      onVerDetalle={onVerDetalle as unknown as ((i: LiquidacionGeneralListItem) => void) | undefined}
    />
  );
}
