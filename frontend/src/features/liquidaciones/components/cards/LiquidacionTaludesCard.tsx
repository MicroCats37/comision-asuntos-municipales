"use client";

import { TALUDES_CONFIG, useLiquidacionCardState } from "../../hooks";
import type { LiquidacionTaludesListItem } from "../../schemas/liquidacion-taludes.schema";
import { LiquidacionCardShell } from "./LiquidacionCardShell";

interface LiquidacionTaludesCardProps {
  item: LiquidacionTaludesListItem;
  onUpdated?: () => void;
}

/**
 * LiquidacionTaludesCard — Card face for a Taludes liquidacion.
 * See `useLiquidacionCardState` + `TALUDES_CONFIG` for behavior + slots.
 */
export function LiquidacionTaludesCard({
  item,
  onUpdated,
}: LiquidacionTaludesCardProps) {
  const { shellProps, modals } = useLiquidacionCardState(
    item,
    TALUDES_CONFIG,
    onUpdated,
  );

  return (
    <>
      <LiquidacionCardShell {...shellProps} />
      {modals}
    </>
  );
}
