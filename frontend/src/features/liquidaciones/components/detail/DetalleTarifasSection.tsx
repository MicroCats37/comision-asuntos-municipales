"use client";

import { Scale } from "lucide-react";
import { formatDecimalPercent } from "@/utils/number-formatter";
import type { PorcentajeObraDatosOut } from "../../schemas/liquidacion-porcentaje.schema";
import { formatCurrency } from "../liquidacion-ui";
import { DetalleField, DetalleSection } from "./DetalleSection";

interface Props {
  /** PorcentajeObra data (Edif / IV / Taludes) */
  lt: PorcentajeObraDatosOut;
}

/**
 * Tarifas aplicadas section. Shown side-by-side with `DetalleDelegadosSection`
 * in the modal's 12-col grid (col-span-6 each).
 *
 * Renders the parametrización (% de liquidación + valor + derecho min/max)
 * on top, then the compact tarifas table.
 */
export function DetalleTarifasSection({ lt }: Props) {
  const detalles = lt.detalles ?? [];
  const count = detalles.length;
  const subtotalSum = detalles.reduce((acc, d) => acc + (d.subtotal ?? 0), 0);

  return (
    <DetalleSection
      title="Cotización"
      icon={Scale}
      badge={count > 0 ? `${count}` : undefined}
      className="lg:col-span-6"
      contentClassName="p-0"
    >
      {/* Parametrización strip */}
      <div className="flex flex-wrap items-baseline gap-x-5 gap-y-1 px-4 py-3 border-b border-border/40 bg-muted/20">
        <DetalleField label="Valor Declarado" mono>
          {formatCurrency(lt.valor_declarado ?? 0)}
        </DetalleField>
        <DetalleField label="% Liq.">
          <span className="text-base font-black text-primary tabular-nums">
            {formatDecimalPercent(lt.porcentaje_liquidacion)}
          </span>
        </DetalleField>
        {lt.derecho_minimo != null ? (
          <DetalleField label="Der. Mín." mono>
            {formatCurrency(lt.derecho_minimo)}
          </DetalleField>
        ) : null}
        {lt.derecho_maximo != null ? (
          <DetalleField label="Der. Máx." mono>
            {formatCurrency(lt.derecho_maximo)}
          </DetalleField>
        ) : null}
        <DetalleField label="% Mín. UIT">
          <span className="font-mono tabular-nums">
            {formatDecimalPercent(lt.porcentaje_minimo_uit)}
          </span>
        </DetalleField>
      </div>

      {/* Tarifas table */}
      {count > 0 ? (
        <div className="divide-y divide-border/20">
          <div className="grid grid-cols-[1fr_auto_auto] gap-x-4 px-4 py-2 bg-muted/15 text-[9px] font-bold text-muted-foreground uppercase tracking-wider">
            <span>Especialidad</span>
            <span className="text-right min-w-[4rem]">% Aplicado</span>
            <span className="text-right min-w-[5rem]">Subtotal</span>
          </div>
          {detalles.map((d) => (
            <div
              key={d.id}
              className="grid grid-cols-[1fr_auto_auto] gap-x-4 px-4 py-2 text-[11px] items-baseline"
            >
              <span className="text-foreground truncate">
                {d.especialidad?.nombre ?? "Tarifa"}
              </span>
              <span className="text-primary font-semibold tabular-nums text-right min-w-[4rem]">
                {formatDecimalPercent(d.porcentaje_aplicado)}
              </span>
              <span className="font-semibold tabular-nums text-right min-w-[5rem]">
                {formatCurrency(d.subtotal)}
              </span>
            </div>
          ))}
          <div className="flex items-baseline gap-x-3 px-4 py-2 bg-primary/5 border-t border-primary/20 text-xs">
            <span className="font-bold uppercase tracking-wider text-primary text-[10px]">
              Σ
            </span>
            <span className="font-semibold text-foreground/80 text-[10px] uppercase tracking-wider">
              Total
            </span>
            <span className="ml-auto font-mono tabular-nums font-bold text-primary">
              {formatCurrency(subtotalSum)}
            </span>
          </div>
        </div>
      ) : (
        <p className="px-4 py-3 text-xs text-muted-foreground/60 italic">
          Sin tarifas registradas.
        </p>
      )}
    </DetalleSection>
  );
}
