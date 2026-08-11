/**
 * Tipos para el stepper de Liquidación Edificaciones.
 */

import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import type { FieldValues, UseFormReturn } from "react-hook-form";
import type {
  MunicipalidadOption,
  VariablesFinancieras,
} from "../types/liquidacion-edificaciones";
import type { RevisionVigente } from "../types/revisiones-vigentes";

// ── Props ────────────────────────────────────────────────────────────────────

export interface LiquidacionStepperModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

// ── Step Render Props (flat, no circular store refs) ─────────────────────────

export interface StepRenderProps {
  methods: UseFormReturn<FieldValues>;
  currentStep: number;
  isActive: boolean;
}

export interface StepConfig {
  id: string;
  title: string;
  description?: string;
  icon?: LucideIcon;
  validate?: (ctx: {
    methods: UseFormReturn<FieldValues>;
    currentStep: number;
  }) => Promise<boolean> | boolean;
  render: (ctx: StepRenderProps) => ReactNode;
}

// ── Confirmation card ─────────────────────────────────────────────────────────

export interface ConfirmacionCardProps {
  title: string;
  icon: LucideIcon;
  onEdit?: () => void;
  children: ReactNode;
  className?: string;
}

// ── Data hooks result types ───────────────────────────────────────────────────

export interface UseLiquidacionDataResult {
  revisionesVigentes: RevisionVigente[] | undefined;
  isLoadingRevisiones: boolean;
  municipalidades: MunicipalidadOption[] | undefined;
  isLoadingMunicipalidades: boolean;
  variablesFinancieras: VariablesFinancieras | undefined;
  isLoadingVariables: boolean;
  especialidadOptions: Array<{ label: string; value: string }>;
  especialidadLabels: Record<string, string>;
}
