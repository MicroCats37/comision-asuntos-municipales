"use client";

import { Eye, EyeOff } from "lucide-react";
import type React from "react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { InputComponentProps } from "./types";

/**
 * Input de contraseña con toggle para mostrar/ocultar
 */
export const InputPassword: React.FC<InputComponentProps> = ({
  field,
  register,
  error,
  id,
}) => {
  const [showPassword, setShowPassword] = useState(false);
  const hasIcon = !!field.icon;
  const Icon = field.icon;

  const togglePasswordVisibility = () => setShowPassword((prev) => !prev);

  return (
    <div className="relative">
      {/* Icon izquierdo (opcional) */}
      {hasIcon && Icon && (
        <div
          className={cn(
            "absolute left-3 top-1/2 -translate-y-1/2 transition-colors duration-200 pointer-events-none z-10",
            error ? "text-destructive" : "text-primary",
          )}
        >
          <Icon className="h-4 w-4" />
        </div>
      )}

      {/* Input */}
      <Input
        id={id}
        type={showPassword ? "text" : "password"}
        placeholder={field.placeholder}
        disabled={field.disabled}
        aria-invalid={!!error}
        className={`${hasIcon ? "pl-10" : ""} pr-10 ${field.className || ""}`}
        {...register(field.name)}
      />

      {/* Toggle button derecho */}
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
        onClick={togglePasswordVisibility}
        tabIndex={-1}
      >
        {showPassword ? (
          <EyeOff className="h-4 w-4 text-muted-foreground" />
        ) : (
          <Eye className="h-4 w-4 text-muted-foreground" />
        )}
        <span className="sr-only">
          {showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
        </span>
      </Button>
    </div>
  );
};
