"use client";

import {
  EDIFICACIONES_CONFIG,
  useLiquidacionCardState,
} from "../../hooks/useLiquidacionCardState";
import type { LiquidacionEdificacionesListItem } from "../../schemas/liquidacion-edificaciones.schema";
import { LiquidacionCardShell } from "./LiquidacionCardShell";

interface LiquidacionEdificacionesCardProps {
  item: LiquidacionEdificacionesListItem;
  onUpdated?: () => void;
}

/**
 * LiquidacionEdificacionesCard — Card face for an Edificacion liquidacion.
 *
 * Behavior (state, modals, action handlers) lives in
 * `useLiquidacionCardState` with `EDIFICACIONES_CONFIG` so it stays in lockstep
 * with the other 5 listing cards.
 */
export function LiquidacionEdificacionesCard({
  item,
  onUpdated,
}: LiquidacionEdificacionesCardProps) {
  const { shellProps, modals } = useLiquidacionCardState(
    item,
    EDIFICACIONES_CONFIG,
    onUpdated,
  );

  return (
    <>
      <LiquidacionCardShell {...shellProps} />
      {modals}
    </>
  );
}
