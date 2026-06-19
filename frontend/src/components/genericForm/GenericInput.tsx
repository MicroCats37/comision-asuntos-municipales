"use client";

import type { LucideIcon } from "lucide-react";
import type { ComponentType, FC, ReactNode } from "react";
import type {
  Control,
  FieldErrors,
  FieldValues,
  UseFormRegister,
} from "react-hook-form";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { getInputComponent } from "./inputs";

// =====================================================================
// 0. NESTED ERROR UTILITY
// =====================================================================

/**
 * Extracts a nested error from a flat error object using dot notation path.
 * Handles paths like "parent.child.field" to access errors.parent.child.field
 */
const getNestedError = (obj: any, path: string) => {
  return path.split(".").reduce((acc, part) => acc && acc[part], obj);
};

// =====================================================================
// 1. WRAPPER DEFINITIONS (Interfaces for Style Injection)
// =====================================================================

/** To wrap a complete SECTION (Card, Accordion, Invisible Div) */
export interface SectionWrapperProps {
  children: ReactNode;
  title?: string;
  description?: string;
  icon?: LucideIcon;
  className?: string;
}

/** To wrap an individual INPUT (Label + Input + Error) */
export interface FieldWrapperProps {
  children: ReactNode;
  field: FormField;
  error?: { message?: string };
  labelId: string;
}

/** Default Wrapper: Standard vertical layout */
export const DefaultFieldWrapper: FC<FieldWrapperProps> = ({
  children,
  field,
  error,
  labelId,
}) => {
  return (
    <div className={`space-y-2 ${field.containerClassName || "col-span-12"}`}>
      {!field.hidden && (
        <Label htmlFor={labelId} className={cn("text-sm font-medium", field.labelClassName)}>
          {field.label}
          {field.required && <span className="text-destructive ml-1">*</span>}
        </Label>
      )}
      {children}
      {error && !field.hidden && (
        <p className="text-sm text-destructive font-medium">{error.message}</p>
      )}
      {field.helperText && !field.hidden && !error && (
        <p className="text-xs text-muted-foreground font-medium px-1">
          {field.helperText}
        </p>
      )}
      {field.description && !field.hidden && field.type !== "checkbox" && (
        <p className="text-xs text-muted-foreground px-1">
          {field.description}
        </p>
      )}
    </div>
  );
};

// =====================================================================
// 2. DATA TYPES
// =====================================================================

export type FieldType =
  | "text"
  | "password"
  | "number"
  | "checkbox"
  | "radio"
  | "select"
  | "textarea"
  | "hidden"
  | "date"
  | "image"
  | "custom"
  | "searchable-select";

export interface FormField {
  name: string;
  label: string;
  type: FieldType;
  defaultValue?: unknown;
  options?: readonly { label: string; value: string | number | boolean }[];
  placeholder?: string;
  description?: string;
  disabled?: boolean;
  isLoading?: boolean;
  helperText?: string;
  hidden?: boolean | ((values: any) => boolean);
  valueType?: "string" | "number" | "boolean";

  // Visual Properties
  icon?: LucideIcon;
  className?: string; // Input/control styling
  labelClassName?: string; // Label-only styling
  containerClassName?: string;
  required?: boolean;
}

export interface FormSection {
  title: string;
  icon?: LucideIcon;
  description?: string;
  className?: string;
  fields: FormField[];
  wrapper?: ComponentType<SectionWrapperProps>;
}

// =====================================================================
// 3. GENERIC INPUT COMPONENT (Refactored with Registry)
// =====================================================================

interface GenericInputProps {
  field: FormField;
  register: UseFormRegister<FieldValues>;
  control: Control<FieldValues>;
  errors: FieldErrors;
  FieldWrapper?: ComponentType<FieldWrapperProps>;
}

export const GenericInput: FC<GenericInputProps> = ({
  field,
  register,
  control,
  errors,
  FieldWrapper = DefaultFieldWrapper,
}) => {
  const error = getNestedError(errors, field.name) as
    | { message?: string }
    | undefined;
  const labelId = field.name;

  // Skip custom fields (handled externally via customFields prop in GenericForm)
  if (field.type === "custom") return null;

  // Hidden inputs don't need a wrapper
  if (field.hidden || field.type === "hidden") {
    const HiddenInput = getInputComponent("hidden");
    return (
      <HiddenInput
        field={field}
        register={register}
        control={control}
        error={error}
        id={labelId}
      />
    );
  }

  // Get component from registry
  const InputComponent = getInputComponent(field.type);

  // Render input inside wrapper
  return (
    <FieldWrapper field={field} error={error} labelId={labelId}>
      <InputComponent
        field={field}
        register={register}
        control={control}
        error={error}
        id={labelId}
      />
    </FieldWrapper>
  );
};
