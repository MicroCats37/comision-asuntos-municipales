"use client";

import { INSPECCION_OBRA_CONFIG, useLiquidacionCardState } from "../../hooks";
import type { LiquidacionInspeccionObraListItem } from "../../schemas/liquidacion-inspeccion-obra.schema";
import { LiquidacionCardShell } from "./LiquidacionCardShell";

interface LiquidacionInspeccionObraCardProps {
  item: LiquidacionInspeccionObraListItem;
  onUpdated?: () => void;
}

/**
 * LiquidacionInspeccionObraCard — Card face for an Inspección de Obra
 * liquidacion. IO uses Inspectores instead of Delegados, so the card
 * config sets `showDelegados: false` and skips the Delegados slot/modal.
 * See `useLiquidacionCardState` + `INSPECCION_OBRA_CONFIG`.
 */
export function LiquidacionInspeccionObraCard({
  item,
  onUpdated,
}: LiquidacionInspeccionObraCardProps) {
  const { shellProps, modals } = useLiquidacionCardState(
    item,
    INSPECCION_OBRA_CONFIG,
    onUpdated,
  );

  return (
    <>
      <LiquidacionCardShell {...shellProps} />
      {modals}
    </>
  );
}
