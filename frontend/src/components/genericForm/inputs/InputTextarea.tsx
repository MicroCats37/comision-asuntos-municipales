// genericForm/inputs/InputTextarea.tsx
"use client";

import type React from "react";
import { Textarea } from "@/components/ui/textarea";
import type { InputComponentProps } from "./types";

/**
 * Textarea multilínea.
 * Soporta icono opcional a la izquierda.
 */
export const InputTextarea: React.FC<InputComponentProps> = ({
  field,
  register,
  error,
  id,
}) => {
  const hasIcon = !!field.icon;
  const Icon = field.icon;

  const textareaElement = (
    <Textarea
      id={id}
      rows={3}
      placeholder={field.placeholder}
      disabled={field.disabled}
      aria-invalid={!!error}
      className={`${hasIcon ? "pl-10" : ""} ${field.className || ""}`}
      {...register(field.name)}
    />
  );

  if (!hasIcon) return textareaElement;

  return (
    <div className="relative">
      <div className="absolute left-3 top-3 text-muted-foreground pointer-events-none">
        {Icon && <Icon className="h-4 w-4" />}
      </div>
      {textareaElement}
    </div>
  );
};
