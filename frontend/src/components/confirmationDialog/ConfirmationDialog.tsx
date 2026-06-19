"use client";

import type { ReactNode } from "react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";

interface ConfirmationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  variant?: "default" | "danger";
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
}: ConfirmationDialogProps) {
  return (
    <GenericModal open={open} onOpenChange={onOpenChange}>
      <GenericModal.Content>
        <GenericModal.Header title={title} description={description} />
        <GenericModal.Footer>
          <GenericModal.Close asChild>
            <Button variant="outline">{cancelLabel}</Button>
          </GenericModal.Close>
          <Button
            variant={variant === "danger" ? "destructive" : "default"}
            onClick={() => {
              onConfirm();
              onOpenChange(false);
            }}
          >
            {confirmLabel}
          </Button>
        </GenericModal.Footer>
      </GenericModal.Content>
    </GenericModal>
  );
}
