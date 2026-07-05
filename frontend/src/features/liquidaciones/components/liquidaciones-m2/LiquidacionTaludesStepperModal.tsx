/**
 * LiquidacionTaludesStepperModal — Wrapper para Taludes.
 * Thin wrapper sobre LiquidacionM2StepperModal.
 */
"use client";

import type { LiquidacionM2StepperModalProps } from "./LiquidacionM2StepperModal";
import { LiquidacionM2StepperModal } from "./LiquidacionM2StepperModal";

export function LiquidacionTaludesStepperModal(
  props: Omit<LiquidacionM2StepperModalProps, "kind">,
) {
  return <LiquidacionM2StepperModal {...props} kind="taludes" />;
}
