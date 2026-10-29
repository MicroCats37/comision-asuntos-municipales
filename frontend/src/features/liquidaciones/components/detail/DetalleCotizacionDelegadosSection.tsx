"use client";

import { FileText, Scale, UserCog } from "lucide-react";
import type { LiquidacionDelegadoEnGeneralOutput } from "@/features/liquidaciones/schemas/liquidacion-base.schema";
import type { EdificacionesPorcentajeObraDatosOut } from "@/features/liquidaciones/schemas/liquidacion-edificaciones.schema";
import type { PorcentajeObraDatosOut } from "@/features/liquidaciones/schemas/liquidacion-porcentaje.schema";
import { formatDecimalPercent } from "@/utils/number-formatter";
import { formatCurrency } from "../liquidacion-ui";
import { DetalleSection } from "./DetalleSection";

interface Props {
  lt: PorcentajeObraDatosOut | EdificacionesPorcentajeObraDatosOut;
  delegados?: LiquidacionDelegadoEnGeneralOutput[];
}

/**
 * Combined section: Tarifas + Delegados grouped by Especialidad.
 * One row per Especialidad shows the tarifas for that specialty on the
 * left and the delegados assigned to that specialty on the right.
 * Surfaces the relationship tarifa ↔ delegado ↔ especialidad.
 *
 * Layout: 4-column mini-table (Especialidad | % Aplicado | Subtotal | Delegado)
 * with a Σ Total row at the bottom.
 */
export function DetalleCotizacionDelegadosSection({ lt, delegados }: Props) {
  const detalles = lt.detalles ?? [];

  // Group tarifas by Especialidad.nombre
  const tarifasByEsp = new Map<string, typeof detalles>();
  for (const d of detalles) {
    const esp = d.especialidad?.nombre ?? "Sin especialidad";
    if (!tarifasByEsp.has(esp)) tarifasByEsp.set(esp, []);
    tarifasByEsp.get(esp)?.push(d);
  }

  // Group delegados by Especialidad.nombre
  const delegadosList = delegados ?? [];
  const delegadosByEsp = new Map<
    string,
    LiquidacionDelegadoEnGeneralOutput[]
  >();
  for (const d of delegadosList) {
    const esp = d.delegado.especialidad?.nombre ?? "Sin especialidad";
    if (!delegadosByEsp.has(esp)) delegadosByEsp.set(esp, []);
    delegadosByEsp.get(esp)?.push(d);
  }

  const especialidades = Array.from(
    new Set([...tarifasByEsp.keys(), ...delegadosByEsp.keys()]),
  ).sort();
  const totalTarifas = detalles.length;
  const totalDelegados = delegadosList.length;
  const totalSubtotal = detalles.reduce((acc, d) => acc + (d.subtotal ?? 0), 0);

  // 4 columnas: Especialidad | % Aplicado | Subtotal | Delegado
  // lg+: 4 cols. <lg: stack each cell under its header.
  const ROW_COLS =
    "grid grid-cols-1 lg:grid-cols-[minmax(0,1.4fr)_minmax(5rem,auto)_minmax(6rem,auto)_minmax(0,1.6fr)]";

  return (
    <DetalleSection
      title="Cotización y Delegados"
      icon={Scale}
      badge={
        <span className="flex items-center gap-1">
          <Scale className="h-3 w-3" />
          {totalTarifas}
          <span className="opacity-60">·</span>
          <UserCog className="h-3 w-3" />
          {totalDelegados}
        </span>
      }
      className="lg:col-span-12"
    >
      <div className="px-4 py-3 flex flex-col gap-3">
        {/* Header row */}
        <div
          className={`${ROW_COLS} gap-x-4 px-2 pb-2 border-b border-border/40 text-[10px] font-bold text-muted-foreground uppercase tracking-wider`}
        >
          <span>Especialidad</span>
          <span className="lg:text-right">% Aplicado</span>
          <span className="lg:text-right">Subtotal</span>
          <span>Delegado</span>
        </div>

        {especialidades.map((esp) => {
          const tars = tarifasByEsp.get(esp) ?? [];
          const dels = delegadosByEsp.get(esp) ?? [];
          return (
            <div
              key={esp}
              className={`${ROW_COLS} gap-x-4 gap-y-1 px-2 py-2.5 rounded-md bg-muted/20 border border-border/40`}
            >
              {/* Especialidad */}
              <div className="flex items-baseline gap-2 min-w-0">
                <span className="font-semibold text-foreground text-sm [text-wrap:balance]">
                  {esp}
                </span>
              </div>

              {/* % Aplicado (stacked if multiple) */}
              <div className="flex flex-col gap-0.5 lg:items-end min-w-0">
                {tars.length === 0 ? (
                  <span className="text-[10px] text-muted-foreground/50 italic">
                    —
                  </span>
                ) : (
                  tars.map((t) => (
                    <span
                      key={t.id}
                      className="font-mono text-xs text-foreground/80 tabular-nums"
                    >
                      {formatDecimalPercent(t.porcentaje_aplicado)}
                    </span>
                  ))
                )}
              </div>

              {/* Subtotal (stacked if multiple) */}
              <div className="flex flex-col gap-0.5 lg:items-end min-w-0">
                {tars.length === 0 ? (
                  <span className="text-[10px] text-muted-foreground/50 italic">
                    —
                  </span>
                ) : (
                  tars.map((t) => (
                    <span
                      key={t.id}
                      className="font-mono text-primary tabular-nums font-semibold text-xs"
                    >
                      {formatCurrency(t.subtotal)}
                    </span>
                  ))
                )}
              </div>

              {/* Delegado (stacked if multiple) */}
              <div className="flex flex-col gap-1 min-w-0">
                {dels.length === 0 ? (
                  <span className="text-[10px] text-muted-foreground/50 italic">
                    Sin delegado
                  </span>
                ) : (
                  dels.map((d) => {
                    const tipo = d.delegado.tipo;
                    return (
                      <div
                        key={d.delegado.id}
                        className="flex flex-wrap items-center gap-x-1.5 text-xs"
                      >
                        <UserCog className="h-3 w-3 text-muted-foreground/60 shrink-0" />
                        <span className="font-semibold text-foreground truncate">
                          {d.delegado.nombre_completo ?? "—"}
                        </span>
                        {tipo ? (
                          <span
                            className={
                              "inline-flex items-center rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider " +
                              (tipo === "TITULAR"
                                ? "bg-primary/10 text-primary"
                                : "bg-secondary text-secondary-foreground/80")
                            }
                          >
                            {tipo}
                          </span>
                        ) : null}
                        <span className="font-mono text-muted-foreground text-[10px]">
                          CIP {d.delegado.cip ?? "—"}
                        </span>
                        {d.datos?.dictamen_revision ? (
                          <span className="font-mono text-muted-foreground/70 italic text-[10px]">
                            <FileText className="inline h-2.5 w-2.5 mr-0.5" />
                            {d.datos.dictamen_revision}
                          </span>
                        ) : null}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          );
        })}

        {/* Total row */}
        {detalles.length > 0 ? (
          <div
            className={`${ROW_COLS} gap-x-4 px-2 pt-2 border-t border-primary/30 items-baseline`}
          >
            <span className="text-[10px] font-bold text-primary uppercase tracking-wider">
              Σ Total
            </span>
            <span className="hidden lg:block" />
            <span className="font-mono font-black text-primary tabular-nums lg:text-right">
              {formatCurrency(totalSubtotal)}
            </span>
            <span className="text-[10px] text-muted-foreground/70 lg:ml-auto">
              {totalTarifas} tarifa{totalTarifas === 1 ? "" : "s"} ·{" "}
              {totalDelegados} delegado
              {totalDelegados === 1 ? "" : "s"}
            </span>
          </div>
        ) : null}
      </div>
    </DetalleSection>
  );
}
