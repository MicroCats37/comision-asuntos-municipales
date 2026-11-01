"use client";

/**
 * RhMensualModalShell — shell COMÚN del wizard de RH mensual
 * (Inspector y Delegado).
 *
 * Sigue el patrón de `LiquidacionFormShell` (forms de Liquidaciones) en lo que
 * importa para un wizard: un único contenedor que aporta la ESTRUCTURA
 * (título create/edit, indicador de pasos, área de error, footer con
 * Back/Next/Cancel/Save y semántica de loading/disabled) mientras cada modal
 * conserva SU CONTENIDO (pasos, columnas, cálculos, payload y validaciones).
 *
 * No se fusionan los pasos de dominio: el shell solo dibuja la estructura.
 */

import { FileSpreadsheet, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import {
  GenericModal,
  type GenericModalSize,
} from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";
import { DialogDescription, DialogTitle } from "@/components/ui/dialog";

// ── Indicador de pasos ────────────────────────────────────────────────────────

export interface RhModalStep {
  icon: LucideIcon;
  /** Etiqueta corta del paso ("Buscar", "Seleccionar", "Confirmar"). */
  label: string;
  /** Descripción larga — se muestra bajo el título del modal. */
  description?: string;
}

/**
 * Indicador de pasos — idéntico para Inspector y Delegado: círculo con icono,
 * estado activo/completado/pendiente y conector entre pasos.
 */
function RhStepIndicator({
  steps,
  currentStep,
}: {
  steps: RhModalStep[];
  currentStep: number;
}) {
  return (
    <div className="flex items-center gap-2 justify-center py-1">
      {steps.map((step, index) => {
        const number = index + 1;
        const StepIcon = step.icon;
        const isActive = currentStep === number;
        const isCompleted = currentStep > number;
        return (
          <div key={step.label} className="flex items-center gap-2">
            <div className="flex flex-col items-center gap-1.5 min-w-[5rem]">
              <div
                className={`flex h-9 w-9 items-center justify-center rounded-full border-2 transition-all ${
                  isActive
                    ? "bg-primary text-primary-foreground border-primary shadow-md shadow-primary/20"
                    : isCompleted
                      ? "bg-primary/15 text-primary border-primary/40"
                      : "bg-secondary/40 text-secondary-foreground/70 border-secondary/50"
                }`}
              >
                <StepIcon className="h-4 w-4" />
              </div>
              <span
                className={`text-[9px] font-bold uppercase tracking-wider text-center ${
                  isActive
                    ? "text-primary"
                    : isCompleted
                      ? "text-primary/70"
                      : "text-muted-foreground/70"
                }`}
              >
                {number}. {step.label}
              </span>
            </div>
            {number < steps.length && (
              <div
                className={`h-0.5 w-10 rounded ${
                  currentStep > number ? "bg-primary/50" : "bg-secondary/40"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Shell ─────────────────────────────────────────────────────────────────────

export interface RhMensualModalShellProps {
  open: boolean;
  /** Cierre del wizard (resetea el formulario y avisa al padre). */
  onClose: () => void;
  /** Antetítulo uppercase (p. ej. "Recibos de Honorario - Delegados"). */
  eyebrow: string;
  /** Título del wizard — cambia entre create y edit. */
  title: string;
  /** Descripción del paso actual. */
  description?: string;
  /** Pasos del wizard (el shell dibuja el indicador). */
  steps: RhModalStep[];
  /** Paso actual (1-based). */
  currentStep: number;
  /** Hay una mutación en curso → deshabilita el botón de retroceso. */
  isPending?: boolean;
  /** Mensaje de error bloqueante (área de error del shell). */
  error?: string | null;
  /** Etiqueta del botón de retroceso ("Atrás" / "Cancelar"). */
  backLabel: string;
  onBack: () => void;
  /** Botones de acción del paso (depende del dominio y del paso). */
  actions?: ReactNode;
  /** Contenido del paso actual. */
  children: ReactNode;
  /** Contenido adicional dentro del modal (filtros, modales anidados, CloseX). */
  extraContent?: ReactNode;
  /** Tamaño del modal (responsive por defecto en `lg`). */
  size?: GenericModalSize;
}

export function RhMensualModalShell({
  open,
  onClose,
  eyebrow,
  title,
  description,
  steps,
  currentStep,
  isPending = false,
  error,
  backLabel,
  onBack,
  actions,
  children,
  extraContent,
  size = "lg",
}: RhMensualModalShellProps) {
  return (
    <GenericModal open={open} onOpenChange={onClose} preventClose={false}>
      <GenericModal.Content size={size}>
        {/* Título y descripción accesibles: el header visible es propio del
            wizard, pero Radix exige ambos en el DialogContent. */}
        <DialogTitle className="sr-only">{title}</DialogTitle>
        <DialogDescription className="sr-only">
          {description || title}
        </DialogDescription>
        <GenericModal.Header
          title=""
          className="bg-primary/[0.03] border-b border-border px-6 py-5"
        >
          <div className="flex items-center gap-3 w-full">
            <div className="p-2 bg-primary/10 rounded-xl border border-primary/20 shadow-sm shrink-0">
              <FileSpreadsheet className="h-5 w-5 text-primary" />
            </div>
            <div className="flex flex-col gap-0.5 min-w-0 flex-1">
              <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                {eyebrow}
              </span>
              <h2 className="text-2xl font-black tracking-tight text-foreground leading-tight">
                {title}
              </h2>
              {description && (
                <p className="hidden sm:block text-sm text-muted-foreground leading-relaxed">
                  {description}
                </p>
              )}
            </div>
            <div className="w-9 shrink-0" aria-hidden="true" />
          </div>
        </GenericModal.Header>

        <GenericModal.Body className="space-y-6">
          <RhStepIndicator steps={steps} currentStep={currentStep} />

          {error && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-xl border border-destructive/30 bg-destructive/5 px-3 py-2.5 text-sm text-destructive"
            >
              <span className="font-semibold">No se pudo continuar:</span>
              <span>{error}</span>
            </div>
          )}

          {children}
        </GenericModal.Body>

        <GenericModal.Footer className="px-6 py-4 bg-muted/30 border-t border-border">
          <div className="flex items-center justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={onBack}
              disabled={isPending}
              className="h-10 rounded-xl font-semibold"
            >
              {backLabel}
            </Button>
            {actions}
          </div>
        </GenericModal.Footer>

        {extraContent}

        <GenericModal.CloseX />
      </GenericModal.Content>
    </GenericModal>
  );
}
