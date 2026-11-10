"use client";

import { type ReactNode, useEffect, useId, useState } from "react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";
import { DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { TypedConfirmationRule } from "./useConfirmationDialog";

export interface ConfirmationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  variant?: "default" | "danger";
  /** Optional header icon tile (established destructive line). */
  icon?: ReactNode;
  /** Optional header eyebrow (established destructive line). */
  eyebrow?: string;
  /** Optional typed rule. Absent => ordinary confirmation. */
  typedConfirmation?: TypedConfirmationRule;
}

export function ConfirmationDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirmar",
  cancelLabel = "Cancelar",
  onConfirm,
  variant = "default",
  icon,
  eyebrow,
  typedConfirmation,
}: ConfirmationDialogProps) {
  const [typedValue, setTypedValue] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const inputId = useId();
  const promptId = useId();

  const expectedText = typedConfirmation?.expectedText ?? "";
  // A blank expected text makes the rule INACTIVE: ordinary confirmation.
  const ruleActive = expectedText.trim() !== "";
  const isMatch =
    ruleActive &&
    typedValue.trim().toUpperCase() === expectedText.trim().toUpperCase();

  // The typed value never survives a confirmation: it resets when the dialog
  // opens and whenever the expected text changes.
  useEffect(() => {
    setTypedValue("");
    setSubmitted(false);
  }, [open, expectedText]);

  /** Confirms only when the typed rule is satisfied (defence in depth). */
  const handleConfirm = () => {
    if (ruleActive && !isMatch) {
      setSubmitted(true);
      return;
    }
    onConfirm();
    onOpenChange(false);
  };

  return (
    <GenericModal open={open} onOpenChange={onOpenChange}>
      <GenericModal.Content>
        <GenericModal.Header className="bg-primary/[0.03] border-b border-border px-6 py-5 sm:px-8">
          <div className="flex items-center gap-3 w-full">
            {icon && (
              <div className="p-2 sm:p-2.5 bg-primary/10 rounded-xl sm:rounded-2xl border border-primary/20 shadow-sm shrink-0">
                {icon}
              </div>
            )}
            <div className="flex flex-col gap-0.5 min-w-0 flex-1">
              {eyebrow && (
                <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                  {eyebrow}
                </span>
              )}
              <DialogTitle className="text-2xl sm:text-3xl font-black tracking-tight text-foreground leading-tight">
                {title}
              </DialogTitle>
              {description && (
                <DialogDescription className="hidden sm:block max-w-prose text-pretty text-sm text-muted-foreground leading-relaxed">
                  {description}
                </DialogDescription>
              )}
            </div>
          </div>
        </GenericModal.Header>

        {/* Body slot — plain div on purpose (no Radix ScrollArea). */}
        <div className={ruleActive ? "px-6 py-5 sm:px-8" : undefined}>
          {ruleActive && (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                handleConfirm();
              }}
            >
              <Label htmlFor={inputId} className="font-semibold">
                {typedConfirmation?.label ?? "Código de confirmación"}
              </Label>
              <p id={promptId} className="mt-1 text-sm text-muted-foreground">
                {typedConfirmation?.prompt ??
                  "Escribe el código indicado para confirmar la acción."}
              </p>
              <Input
                id={inputId}
                className="mt-2 h-10 sm:w-72"
                value={typedValue}
                onChange={(event) => {
                  setTypedValue(event.target.value);
                  setSubmitted(false);
                }}
                aria-describedby={promptId}
                aria-invalid={submitted && !isMatch}
                autoComplete="off"
              />
              {submitted && !isMatch && (
                <p
                  role="alert"
                  className="mt-2 text-sm font-medium text-destructive"
                >
                  {typedConfirmation?.errorMessage ?? "El código no coincide"}
                </p>
              )}
            </form>
          )}
        </div>

        <GenericModal.Footer className="px-6 py-4 sm:px-8 bg-muted/30 border-t border-border">
          <div className="flex flex-row sm:justify-end items-center gap-2 sm:gap-3">
            <GenericModal.Close asChild>
              <Button
                type="button"
                variant="outline"
                aria-label={cancelLabel}
                className="flex-1 h-10 sm:h-11 rounded-xl font-semibold border border-border/60 hover:border-border hover:bg-background transition-all duration-200 sm:max-w-[120px] text-muted-foreground hover:text-foreground"
              >
                {cancelLabel}
              </Button>
            </GenericModal.Close>
            <Button
              type="button"
              variant={variant === "danger" ? "destructive" : "default"}
              onClick={handleConfirm}
              disabled={ruleActive && !isMatch}
              aria-label={confirmLabel}
              className="flex-1 h-10 sm:h-12 rounded-xl sm:rounded-2xl font-bold shadow-lg gap-2 sm:max-w-[160px] text-base transition-all duration-200 disabled:hover:translate-y-0 disabled:hover:shadow-lg"
            >
              {confirmLabel}
            </Button>
          </div>
        </GenericModal.Footer>
      </GenericModal.Content>
    </GenericModal>
  );
}
