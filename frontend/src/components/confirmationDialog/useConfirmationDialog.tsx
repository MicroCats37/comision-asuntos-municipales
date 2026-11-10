"use client";

import { type ReactNode, useCallback, useState } from "react";
import { ConfirmationDialog } from "./ConfirmationDialog";

/**
 * Optional typed-confirmation rule.
 *
 * A blank/whitespace `expectedText` makes the rule INACTIVE (the dialog stays
 * an ordinary confirmation). The match is trim + case-insensitive exact
 * equality.
 */
export interface TypedConfirmationRule {
  /** Token the user must type. Blank/whitespace => the rule is INACTIVE. */
  expectedText: string;
  /** Instruction line rendered above the input. */
  prompt?: string;
  /** Accessible label of the input. */
  label?: string;
  /** Inline mismatch message. */
  errorMessage?: string;
}

export interface ConfirmOptions {
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "default" | "danger";
  /** Optional header icon tile (established destructive line). */
  icon?: ReactNode;
  /** Optional header eyebrow (established destructive line). */
  eyebrow?: string;
  /** Optional typed rule. Absent => ordinary confirmation. */
  typedConfirmation?: TypedConfirmationRule;
}

export function useConfirmationDialog() {
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<ConfirmOptions | null>(null);
  const [resolveRef, setResolveRef] = useState<
    ((value: boolean) => void) | null
  >(null);

  const confirm = useCallback((opts: ConfirmOptions): Promise<boolean> => {
    return new Promise((resolve) => {
      setOptions(opts);
      setResolveRef(() => resolve);
      setOpen(true);
    });
  }, []);

  const handleConfirm = useCallback(() => {
    resolveRef?.(true);
    setOpen(false);
    setOptions(null);
  }, [resolveRef]);

  const handleCancel = useCallback(() => {
    resolveRef?.(false);
    setOpen(false);
    setOptions(null);
  }, [resolveRef]);

  const Dialog = options ? (
    <ConfirmationDialog
      open={open}
      onOpenChange={(v) => {
        if (!v) handleCancel();
      }}
      title={options.title}
      description={options.description}
      confirmLabel={options.confirmLabel}
      cancelLabel={options.cancelLabel}
      variant={options.variant}
      icon={options.icon}
      eyebrow={options.eyebrow}
      typedConfirmation={options.typedConfirmation}
      onConfirm={handleConfirm}
    />
  ) : null;

  return { confirm, Dialog };
}
