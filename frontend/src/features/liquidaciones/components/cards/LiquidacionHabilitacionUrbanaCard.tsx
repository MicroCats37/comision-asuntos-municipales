"use client";

import {
  HABILITACION_URBANA_CONFIG,
  useLiquidacionCardState,
} from "../../hooks";
import type { LiquidacionHabilitacionUrbanaListItem } from "../../schemas/liquidacion-habilitacion-urbana.schema";
import { LiquidacionCardShell } from "./LiquidacionCardShell";

interface LiquidacionHabilitacionUrbanaCardProps {
  item: LiquidacionHabilitacionUrbanaListItem;
  onUpdated?: () => void;
}

/**
 * LiquidacionHabilitacionUrbanaCard — Card face for a Habilitación Urbana
 * liquidacion. See `useLiquidacionCardState` + `HABILITACION_URBANA_CONFIG`.
 */
export function LiquidacionHabilitacionUrbanaCard({
  item,
  onUpdated,
}: LiquidacionHabilitacionUrbanaCardProps) {
  const { shellProps, modals } = useLiquidacionCardState(
    item,
    HABILITACION_URBANA_CONFIG,
    onUpdated,
  );

  return (
    <>
      <LiquidacionCardShell {...shellProps} />
      {modals}
    </>
  );
}
