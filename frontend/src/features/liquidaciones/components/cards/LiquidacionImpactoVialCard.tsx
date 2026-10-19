"use client";

import { IMPACTO_VIAL_CONFIG, useLiquidacionCardState } from "../../hooks";
import type { LiquidacionImpactoVialListItem } from "../../schemas/liquidacion-impacto-vial.schema";
import { LiquidacionCardShell } from "./LiquidacionCardShell";

interface LiquidacionImpactoVialCardProps {
  item: LiquidacionImpactoVialListItem;
  onUpdated?: () => void;
}

/**
 * LiquidacionImpactoVialCard — Card face for an Impacto Vial liquidacion.
 * See `useLiquidacionCardState` + `IMPACTO_VIAL_CONFIG` for behavior + slots.
 */
export function LiquidacionImpactoVialCard({
  item,
  onUpdated,
}: LiquidacionImpactoVialCardProps) {
  const { shellProps, modals } = useLiquidacionCardState(
    item,
    IMPACTO_VIAL_CONFIG,
    onUpdated,
  );

  return (
    <>
      <LiquidacionCardShell {...shellProps} />
      {modals}
    </>
  );
}
