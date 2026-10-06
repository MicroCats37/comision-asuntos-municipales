// genericForm/inputs/InputHidden.tsx
"use client";

import type { InputComponentProps } from "./types";

/**
 * Input oculto para valores que no se muestran al usuario.
 */
export const InputHidden: React.FC<InputComponentProps> = ({
  field,
  register,
}) => {
  return (
    <input
      type="hidden"
      {...register(field.name, {
        valueAsNumber: typeof field.defaultValue === "number",
      })}
    />
  );
};
