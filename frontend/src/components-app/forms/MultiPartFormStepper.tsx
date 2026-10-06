"use client";

/**
 * MultiPartFormStepper — Reusable multi-step form with independent part schemas.
 *
 * # Architecture
 *
 * Unlike `AppStepperFormModal` which uses a single RHF instance + single schema
 * for all steps, `MultiPartFormStepper` gives each part its **own** RHF form
 * with its own schema, default values, and validation. Parts are **siblings**
 * (only the active one is mounted) and contribute data to a shared **aggregate**.
 *
 * # Data Flow
 *
 * ```
 * Part N valid? ──(yes)──> toAggregate(partData, aggregate) ──> aggregate
 *                              │
 *                              ▼
 *                    mapToFinal(aggregate) ──> finalPayload
 *                              │
 *                         (optional)
 *                              ▼
 *                      finalSchema.parse(finalPayload)
 *                              │
 *                              ▼
 *                         onSubmit(finalPayload)
 * ```
 *
 * # Key Features
 *
 * - Independent GenericForm/RHF form per part (sibling forms, not nested)
 * - Each part has its own schema/default values/render
 * - Data stored into aggregate on valid part
 * - Final payload via `mapToFinal(parts)` + optional finalSchema validation
 * - External inputs/modals via `methods.setValue` / `useController` inside render
 * - Steps can be more personalized than final submit payload
 *
 * # Usage
 *
 * ```tsx
 * <MultiPartFormStepper
 *   parts={[
 *     {
 *       id: "personal",
 *       title: "Datos Personales",
 *       schema: personalSchema,
 *       defaultValues: { nombre: "", apellido: "" },
 *       toAggregate: (data, agg) => ({ ...agg, personal: data }),
 *       render: ({ methods, aggregate, setValue }) => (
 *         <GenericForm schema={personalSchema} ...>
 *       ),
 *     },
 *     {
 *       id: "direccion",
 *       title: "Dirección",
 *       schema: direccionSchema,
 *       defaultValues: { calle: "", ciudad: "" },
 *       toAggregate: (data, agg) => ({ ...agg, direccion: data }),
 *       render: ({ methods, aggregate, setValue }) => (...)
 *     },
 *   ]}
 *   mapToFinal={(agg) => ({ ...agg.personal, ...agg.direccion })}
 *   onSubmit={(data) => api.create(data)}
 * />
 * ```
 */

import { zodResolver } from "@hookform/resolvers/zod";
import type { LucideIcon } from "lucide-react";
import { CheckCircle2, Loader2, X } from "lucide-react";
import type { ReactNode } from "react";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import {
  type DefaultValues,
  type FieldValues,
  FormProvider as RHFProvider,
  type UseFormReturn,
  useForm,
} from "react-hook-form";
import type { ZodType } from "zod";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// ── Part Config Types ────────────────────────────────────────────────────────

/** Context passed to each part's render function */
export interface PartRenderContext<TPart extends FieldValues = FieldValues> {
  /** RHF methods for this part's form */
  methods: UseFormReturn<TPart>;
  /** Shared aggregate containing data from all valid parts */
  aggregate: Record<string, unknown>;
  /**
   * Update a field value in this part's form.
   */
  setValue: UseFormReturn<TPart>["setValue"];
  /**
   * Reset the form to new values.
   */
  reset: UseFormReturn<TPart>["reset"];
}

/** Configuration for a single part/step in the stepper */
export interface PartFormConfig<TPart extends FieldValues = FieldValues> {
  /** Unique identifier for this part */
  id: string;
  /** Display title shown in stepper header */
  title: string;
  /** Optional description shown below title in stepper header */
  description?: string;
  /** Optional icon rendered in stepper header */
  icon?: LucideIcon;
  /** Zod schema for this part's fields */
  schema: ZodType<TPart>;
  /** Default values for this part's form */
  defaultValues: DefaultValues<TPart>;
  /**
   * Transform part data into the shared aggregate.
   * Called when the part is valid and user clicks "Siguiente".
   *
   * @example
   * ```ts
   * toAggregate: (data, agg) => ({ ...agg, personal: data })
   * ```
   */
  toAggregate?: (
    partData: TPart,
    currentAggregate: Record<string, unknown>,
  ) => Record<string, unknown>;
  /**
   * Optional validation beyond what the schema covers.
   * Return `true` to proceed, `false` to block navigation.
   * Called after schema validation passes.
   */
  validatePart?: (ctx: {
    methods: UseFormReturn<TPart>;
    aggregate: Record<string, unknown>;
  }) => Promise<boolean> | boolean;
  /**
   * Render function for this part's form content.
   * Only called when the part is the active step.
   *
   * The render receives `methods` (RHF instance for this part only),
   * `aggregate` (current shared state), and `setValue` helpers.
   */
  render: (ctx: PartRenderContext<TPart>) => ReactNode;
}

// ── Main Component Types ────────────────────────────────────────────────────

export interface MultiPartFormStepperProps {
  /** Open/close state */
  open: boolean;
  /** Callback when open state changes */
  onOpenChange: (open: boolean) => void;
  /** Modal title */
  title: string;
  /** Optional eyebrow text above title */
  eyebrow?: string;
  /** Optional icon shown in header */
  icon?: ReactNode;
  /** Optional description under title */
  description?: string;
  /**
   * Ordered list of part configurations.
   * Each part has its own schema, defaults, and render function.
   */
  parts: PartFormConfig[];
  /**
   * Combines the aggregate (built from validated parts) into the final payload.
   * Called just before `onSubmit`.
   *
   * @example
   * ```ts
   * mapToFinal: (agg) => ({
   *   ...agg.personal,
   *   ...agg.direccion,
   *   tipo: "EDIFICACION",
   * })
   * ```
   */
  mapToFinal: (aggregate: Record<string, unknown>) => unknown;
  /**
   * Optional final Zod schema to validate the complete payload
   * produced by `mapToFinal` before calling `onSubmit`.
   */
  finalSchema?: ZodType;
  /**
   * Called with the validated final payload.
   * Return value is ignored (caller manages async state).
   */
  onSubmit: (data: unknown) => unknown | Promise<unknown>;
  /** Initial aggregate state (empty object by default) */
  initialAggregate?: Record<string, unknown>;
  /**
   * Called whenever the aggregate changes (after a part advances).
   * Useful to sync external state (e.g., URL params, breadcrumbs).
   */
  onAggregateChange?: (aggregate: Record<string, unknown>) => void;
  /**
   * Called when the active step index changes.
   */
  onStepChange?: (stepIndex: number) => void;
  /** Whether the form is in a loading state (disables buttons) */
  isLoading?: boolean;
  /** Label for the primary submit button */
  primaryLabel?: string;
  /** Label shown on primary button while loading */
  primaryLoadingLabel?: string;
  /** Label for cancel button */
  cancelLabel?: string;
  /** Label for back button */
  backLabel?: string;
  /** Label for next/advance button */
  nextLabel?: string;
  /** Prevent closing the modal (e.g., while loading) */
  preventClose?: boolean;
  /** Modal size */
  size?: "sm" | "md" | "lg" | "xl" | "full";
}

// ── Constants ───────────────────────────────────────────────────────────────

const TRANSITION_DURATION = 250; // ms

// ── Stepper Header ─────────────────────────────────────────────────────────

interface StepperHeaderProps {
  parts: PartFormConfig[];
  currentStep: number;
  onStepClick?: (step: number) => void;
}

function StepperHeader({
  parts,
  currentStep,
  onStepClick,
}: StepperHeaderProps) {
  return (
    <nav
      aria-label="Progreso del formulario"
      className="px-6 py-3 border-b border-border bg-muted/20"
    >
      <ol className="flex items-center gap-1">
        {parts.map((part, idx) => {
          const isCompleted = idx < currentStep;
          const isCurrent = idx === currentStep;
          const isClickable = idx < currentStep;
          const PartIcon = part.icon;

          return (
            <li key={part.id} className="flex items-center gap-1">
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
                {PartIcon && <PartIcon className="h-3 w-3" />}
                <span className="hidden sm:inline">{part.title}</span>
              </button>

              {idx < parts.length - 1 && (
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

// ── Animated Step ───────────────────────────────────────────────────────────

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

// ── Part Form Mount ─────────────────────────────────────────────────────────

/**
 * Mounts a single part's RHF form only when active.
 * This avoids nested forms (HTML constraint) while keeping each part
 * fully isolated with its own schema and validation.
 *
 * Exposes form methods imperatively via `formRef` so the parent
 * can trigger validation without prop drilling.
 */
interface PartFormMountProps<T extends FieldValues> {
  part: PartFormConfig<T>;
  aggregate: Record<string, unknown>;
  isActive: boolean;
  onMount: (partId: string, methods: UseFormReturn<T>) => void;
  onNext: (partId: string, methods: UseFormReturn<T>) => void;
}

function PartFormMount<T extends FieldValues>({
  part,
  aggregate,
  isActive,
  onMount,
  onNext,
}: PartFormMountProps<T>) {
  const formId = useId();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const methodsRef = useRef<UseFormReturn<T> | null>(null);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const methods = useForm<T>({
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    resolver: zodResolver(part.schema as any) as any,
    defaultValues: part.defaultValues as DefaultValues<T>,
    mode: "onBlur",
  });

  // Keep ref in sync
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  methodsRef.current = methods as any;

  // Notify parent when mounted and methods are ready
  useEffect(() => {
    if (isActive) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      onMount(part.id, methods as any);
    }
  }, [isActive, part.id, methods, onMount]);

  // Expose handleNext for the parent's "Siguiente" button
  const handleNext = useCallback(async () => {
    if (methodsRef.current) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await onNext(part.id, methodsRef.current as any);
    }
  }, [part.id, onNext]);

  // Register global handler for this part
  useEffect(() => {
    const handler = () => handleNext();
    const key = `mpfs-next-${part.id}`;
    document.addEventListener(key, handler);
    return () => document.removeEventListener(key, handler);
  }, [part.id, handleNext]);

  if (!isActive) return null;

  return (
    <RHFProvider {...methods}>
      <form
        id={formId}
        onSubmit={(e) => {
          e.preventDefault();
          handleNext();
        }}
        noValidate
      >
        {part.render({
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          methods: methods as any,
          aggregate,
          setValue: methods.setValue,
          reset: methods.reset,
        })}
      </form>
    </RHFProvider>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────

export function MultiPartFormStepper({
  open,
  onOpenChange,
  title,
  eyebrow,
  icon,
  description,
  parts,
  mapToFinal,
  finalSchema,
  onSubmit,
  initialAggregate = {},
  onAggregateChange,
  onStepChange,
  isLoading = false,
  primaryLabel = "Enviar",
  primaryLoadingLabel = "Guardando...",
  cancelLabel = "Cancelar",
  backLabel = "Anterior",
  nextLabel = "Siguiente",
  preventClose = false,
  size = "lg",
}: MultiPartFormStepperProps) {
  // Step state — local to this component
  const [currentStep, setCurrentStep] = useState(0);
  const [direction, setDirection] = useState<"forward" | "backward">("forward");
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [pendingStep, setPendingStep] = useState<number | null>(null);

  // Aggregate state — shared across all parts
  const [aggregate, setAggregate] =
    useState<Record<string, unknown>>(initialAggregate);

  // Track the active part's form methods for imperative access
  const activeMethodsRef = useRef<UseFormReturn<FieldValues> | null>(null);

  const totalSteps = parts.length;
  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === totalSteps - 1;

  const currentPart = parts[currentStep];

  // ── Aggregate persistence ────────────────────────────────────────────────

  useEffect(() => {
    onAggregateChange?.(aggregate);
  }, [aggregate, onAggregateChange]);

  useEffect(() => {
    onStepChange?.(currentStep);
  }, [currentStep, onStepChange]);

  // ── Modal lifecycle ──────────────────────────────────────────────────────

  // Reset when modal closes
  useEffect(() => {
    if (!open) {
      setCurrentStep(0);
      setDirection("forward");
      setIsTransitioning(false);
      setPendingStep(null);
      setAggregate(initialAggregate);
      activeMethodsRef.current = null;
    }
  }, [open, initialAggregate]);

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

  // ── Part form event handlers ─────────────────────────────────────────────

  /**
   * Called when a part form mounts (only the active part does).
   * Stores the methods ref so we can call handleSubmit imperatively.
   */
  const handlePartMount = useCallback(
    (partId: string, methods: UseFormReturn<FieldValues>) => {
      // Only track the current step's part
      const partIndex = parts.findIndex((p) => p.id === partId);
      if (partIndex === currentStep) {
        activeMethodsRef.current = methods;
      }
    },
    [currentStep, parts],
  );

  /**
   * Called when "Siguiente" is clicked on a part form.
   * 1. Triggers schema validation
   * 2. If passes, calls optional validatePart()
   * 3. If passes, merges data into aggregate
   * 4. Advances to next step
   */
  const handlePartNext = useCallback(
    async (partId: string, methods: UseFormReturn<FieldValues>) => {
      const partIndex = parts.findIndex((p) => p.id === partId);
      const part = parts[partIndex];
      if (!part) return;

      // Step 1: Schema validation
      const valid = await methods.trigger();
      if (!valid) return;

      // Step 2: Optional custom validation
      if (part.validatePart) {
        const customValid = await part.validatePart({ methods, aggregate });
        if (!customValid) return;
      }

      // Step 3: Merge into aggregate
      const partData = methods.getValues();
      const newAggregate = part.toAggregate
        ? part.toAggregate(
            partData as Parameters<typeof part.toAggregate>[0],
            aggregate,
          )
        : { ...aggregate, [partId]: partData };

      setAggregate(newAggregate);

      // Step 4: Advance (if not last step)
      if (partIndex === totalSteps - 1) return;
      setDirection("forward");
      setIsTransitioning(true);
      setPendingStep(partIndex + 1);
    },
    [parts, aggregate, totalSteps],
  );

  // ── Navigation ────────────────────────────────────────────────────────────

  const handleClose = useCallback(
    (nextOpen: boolean) => {
      if (!nextOpen) onOpenChange(false);
    },
    [onOpenChange],
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

  // Trigger "Siguiente" on the active part form
  const triggerNext = useCallback(() => {
    const event = new CustomEvent(`mpfs-next-${currentPart.id}`);
    document.dispatchEvent(event);
  }, [currentPart?.id]);

  // ── Submit ───────────────────────────────────────────────────────────────

  const handleSubmit = useCallback(
    async (_e: React.FormEvent) => {
      // Build final payload from aggregate
      const finalPayload = mapToFinal(aggregate);

      // Optional final schema validation
      if (finalSchema) {
        try {
          finalSchema.parse(finalPayload);
        } catch {
          // Final schema validation failed — caller should handle error display
          return;
        }
      }

      await onSubmit(finalPayload);
    },
    [aggregate, mapToFinal, finalSchema, onSubmit],
  );

  const activeStep = pendingStep !== null ? pendingStep : currentStep;
  const StepIcon = currentPart?.icon;

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
          parts={parts}
          currentStep={currentStep}
          onStepClick={handleStepClick}
        />

        {/* Body */}
        <GenericModal.Body className="p-0">
          <div className="flex flex-col min-h-0 flex-1 min-w-0">
            {/* Current step heading */}
            <div className="flex items-center gap-2 mb-4 px-6 py-4 sm:px-8">
              {StepIcon && (
                <div className="p-2 bg-primary/10 rounded-lg text-primary">
                  <StepIcon className="h-4 w-4" />
                </div>
              )}
              <div>
                <h3 className="text-base font-bold text-foreground">
                  {currentPart?.title}
                </h3>
                {currentPart?.description && (
                  <p className="text-sm text-muted-foreground">
                    {currentPart.description}
                  </p>
                )}
              </div>
            </div>

            {/* Step panels — only the active step is mounted */}
            <div className="flex-1 min-h-0 min-w-0 px-6 pb-4 sm:px-8">
              {parts.map((part, idx) => (
                <AnimatedStep
                  key={part.id}
                  direction={direction}
                  isActive={idx === activeStep}
                >
                  <PartFormMount
                    part={part}
                    aggregate={aggregate}
                    isActive={idx === activeStep}
                    onMount={handlePartMount}
                    onNext={handlePartNext}
                  />
                </AnimatedStep>
              ))}
            </div>
          </div>
        </GenericModal.Body>

        {/* Footer */}
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
                type="button"
                onClick={handleSubmit}
                disabled={isLoading}
                className="flex-1 h-10 sm:h-12 rounded-xl sm:rounded-2xl font-bold shadow-lg shadow-primary/25 gap-2 sm:max-w-[180px] text-base transition-all duration-200 hover:shadow-xl hover:shadow-primary/30 hover:-translate-y-0.5 active:translate-y-0 disabled:hover:translate-y-0 disabled:hover:shadow-lg"
              >
                {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                <span>{isLoading ? primaryLoadingLabel : primaryLabel}</span>
              </Button>
            ) : (
              <Button
                type="button"
                onClick={triggerNext}
                disabled={isLoading}
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
