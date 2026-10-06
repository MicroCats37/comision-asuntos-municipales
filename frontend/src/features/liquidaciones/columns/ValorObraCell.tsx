"use client";

import { formatCurrency } from "../components/liquidacion-ui";
import type { PorcentajeObraDatosOut } from "../schemas/liquidacion-porcentaje.schema";

interface ValorObraCellProps {
  lt: PorcentajeObraDatosOut;
}

/**
 * Cell showing `valor_declarado` (the base on which % applies).
 * Header context (provided by `extraColumns[…].header`) names this column.
 */
export function ValorObraCell({ lt }: ValorObraCellProps) {
  return (
    <div className="flex flex-col justify-center px-3 py-3.5 min-w-0">
      <span className="text-sm font-semibold text-foreground tabular-nums leading-snug">
        {formatCurrency(lt.valor_declarado ?? 0)}
      </span>
    </div>
  );
}
