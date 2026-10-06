"use client";

import { ChevronRight, FileText, Scale, UserCog } from "lucide-react";
import type { LiquidacionDelegadoEnGeneralOutput } from "@/features/liquidaciones/schemas/liquidacion-base.schema";
import type { PorcentajeObraDatosOut } from "@/features/liquidaciones/schemas/liquidacion-porcentaje.schema";
import { formatCurrency } from "../liquidacion-ui";
import { DetalleSection } from "./DetalleSection";

interface Props {
  lt: PorcentajeObraDatosOut;
  delegados?: LiquidacionDelegadoEnGeneralOutput[];
}

/**
 * Combined section: Tarifas + Delegados grouped by Especialidad.
 * One row per Especialidad shows the tarifas for that specialty on the
 * left and the delegados assigned to that specialty on the right.
 * Surfaces the relationship tarifa ↔ delegado ↔ especialidad.
 */
export function DetalleCotizacionDelegadosSection({ lt, delegados }: Props) {
  const detalles = lt.detalles ?? [];

  // Group tarifas by Especialidad.nombre
  const tarifasByEsp = new Map<string, typeof detalles>();
  for (const d of detalles) {
    const esp = d.especialidad?.nombre ?? "Sin especialidad";
    if (!tarifasByEsp.has(esp)) tarifasByEsp.set(esp, []);
    tarifasByEsp.get(esp)!.push(d);
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
    delegadosByEsp.get(esp)!.push(d);
  }

  const especialidades = Array.from(
    new Set([...tarifasByEsp.keys(), ...delegadosByEsp.keys()]),
  ).sort();
  const totalTarifas = detalles.length;
  const totalDelegados = delegadosList.length;
  const totalSubtotal = detalles.reduce((acc, d) => acc + (d.subtotal ?? 0), 0);

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
        <div className="grid grid-cols-[1fr_auto_auto] gap-x-3 px-2 pb-2 border-b border-border/40 text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
          <span>Especialidad</span>
          <span className="text-right min-w-[6rem]">Tarifa</span>
          <span className="min-w-[10rem]">Delegado</span>
        </div>

        {especialidades.map((esp) => {
          const tars = tarifasByEsp.get(esp) ?? [];
          const dels = delegadosByEsp.get(esp) ?? [];
          return (
            <div
              key={esp}
              className="grid grid-cols-1 lg:grid-cols-[1fr_auto_auto] gap-x-4 gap-y-1 px-2 py-2 rounded-md bg-muted/20 border border-border/40"
            >
              {/* Especialidad */}
              <div className="flex items-baseline gap-2 min-w-0">
                <span className="font-semibold text-foreground text-sm [text-wrap:balance]">
                  {esp}
                </span>
  
              </div>

              {/* Tarifas (stacked if multiple) */}
              <div className="flex flex-col gap-0.5 lg:items-end min-w-[6rem]">
                {tars.length === 0 ? (
                  <span className="text-[10px] text-muted-foreground/50 italic">
                    —
                  </span>
                ) : (
                  tars.map((t) => (
                    <div
                      key={t.id}
                      className="flex items-baseline gap-1 text-xs"
                    >
                      <Scale className="h-2.5 w-2.5 text-muted-foreground/50 shrink-0" />
                      <span className="font-mono text-foreground/80">
                        {t.porcentaje_aplicado != null
                          ? t.porcentaje_aplicado.toLocaleString("es-PE", {
                              minimumFractionDigits: 2,
                              maximumFractionDigits: 4,
                            })
                          : "—"}
                      </span>
                      <span className="font-mono text-primary tabular-nums font-semibold">
                        {formatCurrency(t.subtotal)}
                      </span>
                    </div>
                  ))
                )}
              </div>

              {/* Delegados (stacked if multiple) */}
              <div className="flex flex-col gap-1 min-w-[10rem]">
                {dels.length === 0 ? (
                  <span className="text-[10px] text-muted-foreground/50 italic">
                    Sin delegado
                  </span>
                ) : (
                  dels.map((d, i) => {
                    const tipo = d.delegado.tipo;
                    return (
                      <div
                        key={`d-${i}`}
                        className="flex items-baseline gap-1.5 text-xs"
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

        {/* Total */}
        {detalles.length > 0 ? (
          <div className="flex items-baseline gap-3 px-2 pt-2 border-t border-primary/30">
            <span className="text-[10px] font-bold text-primary uppercase tracking-wider">
              Σ Total
            </span>
            <span className="font-mono font-black text-primary tabular-nums">
              {formatCurrency(totalSubtotal)}
            </span>
            <span className="text-[10px] text-muted-foreground/70 ml-auto">
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
