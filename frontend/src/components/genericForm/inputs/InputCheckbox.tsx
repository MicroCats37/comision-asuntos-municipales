// genericForm/inputs/InputCheckbox.tsx
"use client";

import { Controller } from "react-hook-form";
import { Checkbox } from "@/components/ui/checkbox";
import type { InputComponentProps } from "./types";

/**
 * Checkbox booleano simple.
 * La descripción se muestra inline al lado del checkbox.
 */
export const InputCheckbox: React.FC<InputComponentProps> = ({
  field,
  control,
  id,
}) => {
  return (
    <div className="flex items-center space-x-2 mt-2">
      <Controller
        control={control}
        name={field.name}
        render={({ field: { value, onChange } }) => (
          <Checkbox
            id={id}
            checked={value === true}
            onCheckedChange={onChange} // Shadcn usa onCheckedChange
            disabled={field.disabled}
          />
        )}
      />
      {field.description && (
        <span className="text-sm text-muted-foreground">
          {field.description}
        </span>
      )}
    </div>
  );
};
