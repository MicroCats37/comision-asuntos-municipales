"use client";

import { Banknote, Info, Percent } from "lucide-react";
import type { VariablesFinancierasCardProps } from "../types/liquidacion-edificaciones-form.types";

/** Format IGV as percentage: 0.18 -> "18%" */
const formatIgv = (valor: number): string => {
  if (valor <= 0) return "—";
  return `${(valor * 100).toFixed(0)}%`;
};

/** Format UIT as currency: 5500 -> "S/ 5,500" */
const formatUit = (valor: number): string => {
  if (valor <= 0) return "—";
  return `S/ ${valor.toLocaleString("es-PE")}`;
};

export function VariablesFinancierasCard({
  variables,
  isLoading,
}: VariablesFinancierasCardProps) {
  if (isLoading) {
    return (
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground animate-pulse">
        <div className="h-3 w-16 bg-muted rounded" />
        <div className="h-3 w-20 bg-muted rounded" />
      </div>
    );
  }

  if (!variables) {
    return (
      <div className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground">
        <Info className="h-3.5 w-3.5 text-primary" />
        <span>No disponibles</span>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
      <span className="inline-flex items-center gap-1.5">
        <Percent className="h-3 w-3 text-primary/60 shrink-0" />
        <span>IGV</span>
        <strong className="font-medium text-foreground">
          {formatIgv(variables.igv_valor)}
        </strong>
      </span>
      <span className="inline-flex items-center gap-1.5">
        <Banknote className="h-3 w-3 text-primary/60 shrink-0" />
        <span>UIT</span>
        <strong className="font-medium text-foreground">
          {formatUit(variables.uit_valor)}
        </strong>
      </span>
    </div>
  );
}
