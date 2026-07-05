/**
 * LiquidacionImpactoVialStepperModal — Wrapper para Impacto Vial.
 * Thin wrapper sobre LiquidacionM2StepperModal.
 */
"use client";

import type { LiquidacionM2StepperModalProps } from "./LiquidacionM2StepperModal";
import { LiquidacionM2StepperModal } from "./LiquidacionM2StepperModal";

export function LiquidacionImpactoVialStepperModal(
  props: Omit<LiquidacionM2StepperModalProps, "kind">,
) {
  return <LiquidacionM2StepperModal {...props} kind="impacto-vial" />;
}
