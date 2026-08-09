"use client";

import type { LucideIcon } from "lucide-react";
import { CheckCircle2, Loader2, X } from "lucide-react";
import type { ReactNode } from "react";
import { useCallback, useEffect, useId, useState } from "react";
import type {
  DefaultValues,
  FieldValues,
  UseFormReturn,
} from "react-hook-form";
import type { ZodType } from "zod";
import { GenericForm } from "@/components/genericForm/GenericForm";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface StepConfig {
  id: string;
  title: string;
  description?: string;
  icon?: LucideIcon;
  /**
   * Runs when user clicks "Siguiente".
   * Return `true` to proceed, `false` to block.
   */
  validate?: (ctx: {
    methods: UseFormReturn<FieldValues>;
    currentStep: number;
  }) => Promise<boolean> | boolean;
  render: (ctx: {
    methods: UseFormReturn<FieldValues>;
    currentStep: number;
    isActive: boolean;
  }) => ReactNode;
}

export interface AppStepperFormModalProps<T extends FieldValues> {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  eyebrow?: string;
  icon?: ReactNode;
  description?: string;
  steps: StepConfig[];
  schema: ZodType<T>;
  initialData?: DefaultValues<T>;
  formMethods?: UseFormReturn<T>;
  onSubmit: (data: T) => unknown;
  isLoading?: boolean;
  primaryLabel?: string;
  primaryLoadingLabel?: string;
  cancelLabel?: string;
  backLabel?: string;
  nextLabel?: string;
  preventClose?: boolean;
  size?: "sm" | "md" | "lg" | "xl" | "full";
}

const TRANSITION_DURATION = 250; // ms

// ── Stepper Header ───────────────────────────────────────────────────────────

interface StepperHeaderProps {
  steps: StepConfig[];
  currentStep: number;
  onStepClick?: (step: number) => void;
}

function StepperHeader({
  steps,
  currentStep,
  onStepClick,
}: StepperHeaderProps) {
  return (
    <nav
      aria-label="Progreso del formulario"
      className="px-6 py-3 border-b border-border bg-muted/20"
    >
      <ol className="flex items-center gap-1">
        {steps.map((step, idx) => {
          const isCompleted = idx < currentStep;
          const isCurrent = idx === currentStep;
          const isClickable = idx < currentStep;

          return (
            <li key={step.id} className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => isClickable && onStepClick?.(idx)}
                disabled={!isClickable}
                aria-current={isCurrent ? "step" : undefined}
                className={cn(
                  "flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold transition-all duration-200",
                  "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
                  isCurrent && "bg-primary text-primary-foreground shadow-sm",
                  isCompleted &&
                    "bg-primary/20 text-primary hover:bg-primary/30 cursor-pointer",
                  !isCurrent &&
                    !isCompleted &&
                    "bg-muted text-muted-foreground",
                )}
              >
                {isCompleted ? (
                  <CheckCircle2 className="h-3.5 w-3.5" />
                ) : (
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-current text-[10px] text-white">
                    {idx + 1}
                  </span>
                )}
                <span className="hidden sm:inline">{step.title}</span>
              </button>

              {idx < steps.length - 1 && (
                <div
                  className={cn(
                    "h-px w-4 sm:w-8 transition-colors duration-200",
                    idx < currentStep ? "bg-primary" : "bg-border",
                  )}
                  aria-hidden="true"
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

// ── Animated Step ─────────────────────────────────────────────────────────────

interface AnimatedStepProps {
  children: ReactNode;
  direction: "forward" | "backward";
  isActive: boolean;
}

function AnimatedStep({ children, direction, isActive }: AnimatedStepProps) {
  return (
    <div
      data-state={isActive ? "active" : "inactive"}
      data-direction={direction}
      className={cn(
        "transition-all duration-200 ease-out",
        isActive ? "opacity-100 translate-x-0" : "opacity-0 hidden",
      )}
    >
      {children}
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

export function AppStepperFormModal<T extends FieldValues>({
  open,
  onOpenChange,
  title,
  eyebrow,
  icon,
  description,
  steps,
  schema,
  initialData,
  formMethods,
  onSubmit,
  isLoading = false,
  primaryLabel = "Crear",
  primaryLoadingLabel = "Guardando...",
  cancelLabel = "Cancelar",
  backLabel = "Anterior",
  nextLabel = "Siguiente",
  preventClose = true,
  size = "lg",
}: AppStepperFormModalProps<T>) {
  const formId = useId();

  // Step state — local to this component (generic reusable component)
  const [currentStep, setCurrentStep] = useState(0);
  const [direction, setDirection] = useState<"forward" | "backward">("forward");
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [pendingStep, setPendingStep] = useState<number | null>(null);

  const totalSteps = steps.length;
  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === totalSteps - 1;

  const handleFormSubmit = useCallback(
    async (data: T) => {
      await onSubmit(data);
    },
    [onSubmit],
  );

  const handleClose = useCallback(
    (nextOpen: boolean) => {
      if (!nextOpen) onOpenChange(false);
    },
    [onOpenChange],
  );

  // Navigation with optional per-step validation
  const handleNext = useCallback(
    async (methods: UseFormReturn<T>) => {
      const step = steps[currentStep];
      if (step?.validate) {
        const isValid = await step.validate({
          methods: methods as unknown as UseFormReturn<FieldValues>,
          currentStep,
        });
        if (!isValid) return;
      }
      if (isLastStep) return;
      setDirection("forward");
      setIsTransitioning(true);
      setPendingStep(currentStep + 1);
    },
    [currentStep, steps, isLastStep],
  );

  const handleBack = useCallback(() => {
    if (isFirstStep) return;
    setDirection("backward");
    setIsTransitioning(true);
    setPendingStep(currentStep - 1);
  }, [isFirstStep, currentStep]);

  const handleStepClick = useCallback(
    (step: number) => {
      if (step < currentStep) {
        setDirection("backward");
        setIsTransitioning(true);
        setPendingStep(step);
      }
    },
    [currentStep],
  );

  // Commit step change after transition animation
  useEffect(() => {
    if (isTransitioning && pendingStep !== null) {
      const timer = setTimeout(() => {
        setCurrentStep(pendingStep);
        setIsTransitioning(false);
        setPendingStep(null);
      }, TRANSITION_DURATION);
      return () => clearTimeout(timer);
    }
  }, [isTransitioning, pendingStep]);

  // Reset stepper when modal closes
  useEffect(() => {
    if (!open) {
      setCurrentStep(0);
      setDirection("forward");
      setIsTransitioning(false);
      setPendingStep(null);
    }
  }, [open]);

  const currentStepConfig = steps[currentStep];
  const StepIcon = currentStepConfig?.icon;
  const activeStep = pendingStep !== null ? pendingStep : currentStep;

  return (
    <GenericModal
      open={open}
      onOpenChange={handleClose}
      preventClose={preventClose || isLoading}
    >
      <GenericModal.Content>
        {/* Header */}
        <GenericModal.Header
          title=""
          className="bg-primary/[0.03] border-b border-border px-6 py-5 sm:px-8"
        >
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
              <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-foreground leading-tight">
                {title}
              </h2>
              {description && (
                <p className="hidden sm:block max-w-prose text-pretty line-clamp-3 text-sm text-muted-foreground leading-relaxed">
                  {description}
                </p>
              )}
            </div>
            <div className="w-9 sm:w-11 shrink-0" aria-hidden="true" />
          </div>
        </GenericModal.Header>

        {/* Stepper Progress */}
        <StepperHeader
          steps={steps}
          currentStep={currentStep}
          onStepClick={handleStepClick}
        />

        {/* Body */}
        <GenericModal.Body className="p-0">
          <GenericForm
            formId={formId}
            schema={schema}
            initialData={initialData}
            formMethods={formMethods as UseFormReturn<T>}
            onSubmit={handleFormSubmit as (data: T) => unknown}
            isLoading={isLoading}
            skipFooter
            formClassName="flex flex-col"
          >
            {() => {
              return (
                <div className="flex flex-col min-h-0 flex-1 min-w-0">
                  {/* Step content area */}
                  <div className="flex-1 min-h-0 min-w-0 max-w-full">
                    {/* Current step heading */}
                    <div className="flex items-center gap-2 mb-4">
                      {StepIcon && (
                        <div className="p-2 bg-primary/10 rounded-lg text-primary">
                          <StepIcon className="h-4 w-4" />
                        </div>
                      )}
                      <div>
                        <h3 className="text-base font-bold text-foreground">
                          {currentStepConfig?.title}
                        </h3>
                        {currentStepConfig?.description && (
                          <p className="text-sm text-muted-foreground">
                            {currentStepConfig.description}
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Step panels — only the active step is visible */}
                    {steps.map((step, idx) => (
                      <AnimatedStep
                        key={step.id}
                        direction={direction}
                        isActive={idx === activeStep}
                      >
                        {step.render({
                          methods:
                            formMethods as unknown as UseFormReturn<FieldValues>,
                          currentStep: idx,
                          isActive: idx === currentStep,
                        })}
                      </AnimatedStep>
                    ))}
                  </div>
                </div>
              );
            }}
          </GenericForm>
        </GenericModal.Body>

        {/* Footer — CORRECT: Outside scrollable body, using GenericModal.Footer */}
        <GenericModal.Footer className="px-6 py-4 sm:px-8 bg-muted/30 border-t border-border">
          <div className="flex flex-row sm:justify-end items-center gap-2 sm:gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isLoading}
              className="flex-1 h-10 sm:h-11 rounded-xl font-semibold border border-border/60 hover:border-border hover:bg-background transition-all duration-200 sm:max-w-[120px] text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4 sm:hidden" />
              <span className="hidden sm:inline">{cancelLabel}</span>
            </Button>

            {!isFirstStep && (
              <Button
                type="button"
                variant="outline"
                onClick={handleBack}
                disabled={isLoading || isFirstStep}
                className="flex-1 h-10 sm:h-11 rounded-xl font-semibold border border-border/60 hover:border-border hover:bg-background transition-all duration-200 sm:max-w-[120px]"
              >
                {backLabel}
              </Button>
            )}

            {isLastStep ? (
              <Button
                type="submit"
                form={formId}
                disabled={isLoading}
                className="flex-1 h-10 sm:h-12 rounded-xl sm:rounded-2xl font-bold shadow-lg shadow-primary/25 gap-2 sm:max-w-[180px] text-base transition-all duration-200 hover:shadow-xl hover:shadow-primary/30 hover:-translate-y-0.5 active:translate-y-0 disabled:hover:translate-y-0 disabled:hover:shadow-lg"
              >
                {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                <span>{isLoading ? primaryLoadingLabel : primaryLabel}</span>
              </Button>
            ) : (
              <Button
                type="button"
                onClick={() => formMethods && handleNext(formMethods)}
                disabled={isLoading || !formMethods}
                className="flex-1 h-10 sm:h-12 rounded-xl sm:rounded-2xl font-bold shadow-lg shadow-primary/25 gap-2 sm:max-w-[160px] text-base transition-all duration-200 hover:shadow-xl hover:shadow-primary/30 hover:-translate-y-0.5 active:translate-y-0 disabled:hover:translate-y-0 disabled:hover:shadow-lg"
              >
                {nextLabel}
              </Button>
            )}
          </div>
        </GenericModal.Footer>

        <GenericModal.CloseX />
      </GenericModal.Content>
    </GenericModal>
  );
}
