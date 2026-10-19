"use client";

import { MECANICA_SUELOS_CONFIG, useLiquidacionCardState } from "../../hooks";
import type { LiquidacionMecanicaSuelosListItem } from "../../schemas/liquidacion-mecanica-suelos.schema";
import { LiquidacionCardShell } from "./LiquidacionCardShell";

interface LiquidacionMecanicaSuelosCardProps {
  item: LiquidacionMecanicaSuelosListItem;
  onUpdated?: () => void;
}

/**
 * LiquidacionMecanicaSuelosCard — Card face for a Mecánica de Suelos
 * liquidacion. See `useLiquidacionCardState` + `MECANICA_SUELOS_CONFIG`.
 */
export function LiquidacionMecanicaSuelosCard({
  item,
  onUpdated,
}: LiquidacionMecanicaSuelosCardProps) {
  const { shellProps, modals } = useLiquidacionCardState(
    item,
    MECANICA_SUELOS_CONFIG,
    onUpdated,
  );

  return (
    <>
      <LiquidacionCardShell {...shellProps} />
      {modals}
    </>
  );
}
