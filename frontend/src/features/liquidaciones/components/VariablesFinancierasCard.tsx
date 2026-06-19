"use client";

import { Info, Percent, Banknote } from "lucide-react";
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
      <div className="flex items-start gap-3 p-4 rounded-xl border border-primary/30 bg-primary/5 animate-pulse">
        <div className="h-5 w-5 bg-primary/20 rounded" />
        <div className="space-y-2 flex-1">
          <div className="h-4 w-40 bg-primary/20 rounded" />
          <div className="space-y-1">
            <div className="h-3 w-12 bg-primary/20 rounded" />
            <div className="h-3 w-16 bg-primary/20 rounded" />
          </div>
        </div>
      </div>
    );
  }

  if (!variables) {
    return (
      <div className="flex items-start gap-3 p-4 rounded-xl border border-primary/30 bg-primary/5">
        <Info className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
        <div className="space-y-1 text-xs">
          <p className="font-semibold text-primary">
            Variables Financieras Vigentes
          </p>
          <p className="text-muted-foreground italic">
            No se pudieron cargar las variables financieras
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 p-4 rounded-xl border border-primary/30 bg-primary/5">
      <div className="flex flex-col gap-1 mt-0.5">
        <Percent className="h-4 w-4 text-primary" />
        <Banknote className="h-4 w-4 text-primary/70" />
      </div>
      <div className="space-y-1 text-xs">
        <p className="font-semibold text-primary uppercase tracking-wide">
          Variables Financieras Vigentes
        </p>
        <div className="space-y-0.5">
          <span className="flex items-center gap-1.5 text-foreground">
            <Percent className="h-3 w-3 text-primary/70" />
            IGV: <strong className="text-primary">{formatIgv(variables.igv_valor)}</strong>
          </span>
          <span className="flex items-center gap-1.5 text-foreground">
            <Banknote className="h-3 w-3 text-primary/70" />
            UIT: <strong className="text-primary">{formatUit(variables.uit_valor)}</strong>
          </span>
          <span className="text-[10px] text-muted-foreground/70">
            Período: {variables.igv_periodo_inicio || "—"}
          </span>
        </div>
      </div>
    </div>
  );
}
