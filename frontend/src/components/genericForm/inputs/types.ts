// genericForm/inputs/types.ts
// Tipos compartidos para todos los inputs del registry

import type { LucideIcon } from "lucide-react";
import type React from "react";
import type { Control, FieldValues, UseFormRegister } from "react-hook-form";

/** Opciones para select, radio, etc. */
export interface InputOption {
  label: string;
  value: string | number | boolean | null;
}

/** Configuración base de un campo de formulario */
export interface FieldConfig {
  name: string;
  label: string;
  type: string;
  placeholder?: string;
  description?: string;
  disabled?: boolean;
  required?: boolean;
  hidden?: boolean | ((values: any) => boolean);

  // Para select/radio
  options?: readonly InputOption[];
  isLoading?: boolean;

  // Visuales
  icon?: LucideIcon;
  className?: string; // Clases del input interno
  containerClassName?: string; // Clases del grid container (ej: col-span-6)
  helperText?: string; // Texto de ayuda debajo del input

  // Type coercion
  valueType?: "string" | "number" | "boolean";
  defaultValue?: unknown;
}

/** Props que recibe cada componente de input del registry */
export interface InputComponentProps<
  TFieldValues extends FieldValues = FieldValues,
> {
  field: FieldConfig;
  register: UseFormRegister<TFieldValues>;
  control: Control<TFieldValues>;
  error?: { message?: string };
  id: string;
}

/** Tipo para los componentes del registry */
export type InputComponent<TFieldValues extends FieldValues = FieldValues> =
  React.FC<InputComponentProps<TFieldValues>>;
