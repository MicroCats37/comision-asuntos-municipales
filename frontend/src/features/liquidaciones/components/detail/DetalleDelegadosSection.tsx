"use client";

import { Users } from "lucide-react";
import type { LiquidacionDelegadoEnGeneralOutput } from "@/features/liquidaciones/schemas/liquidacion-base.schema";
import { DetalleSection } from "./DetalleSection";

interface Props {
  delegados: LiquidacionDelegadoEnGeneralOutput[] | undefined | null;
}

/**
 * Delegates section grouped by specialty. Each specialty gets its own
 * sub-list; each delegado shows nombre_completo, CIP, dictamen and
 * tipo (TITULAR / ALTERNO).
 */
export function DetalleDelegadosSection({ delegados }: Props) {
  const list = delegados ?? [];
  if (list.length === 0) return null;

  // Group by specialty.
  const groups = new Map<string, LiquidacionDelegadoEnGeneralOutput[]>();
  for (const d of list) {
    const key = d.delegado.especialidad?.nombre ?? "Sin especialidad";
    const arr = groups.get(key) ?? [];
    arr.push(d);
    groups.set(key, arr);
  }

  return (
    <DetalleSection
      title="Delegados"
      icon={Users}
      badge={`${list.length} ${list.length === 1 ? "asignado" : "asignados"}`}
      className="lg:col-span-6"
    >
      <div className="space-y-4">
        {Array.from(groups.entries()).map(([especialidad, items]) => (
          <div key={especialidad} className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center rounded-md bg-primary/10 text-primary px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                {especialidad}
              </span>
              <span className="text-[10px] text-muted-foreground">
                {items.length} {items.length === 1 ? "delegado" : "delegados"}
              </span>
            </div>
            <div className="space-y-1.5">
              {items.map((d, _i) => {
                const tipo = d.delegado.tipo;
                return (
                  <div
                    key={`${especialidad}-${d.delegado?.id ?? d.delegado?.cip ?? "unknown"}`}
                    className="flex items-center justify-between gap-2 rounded-md border border-border/40 bg-muted/20 px-2.5 py-1.5 text-xs"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="font-semibold text-foreground truncate">
                        {d.delegado.nombre_completo ?? "-"}
                      </div>
                      <div className="flex items-center gap-1.5 mt-0.5">
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
                        {d.datos?.dictamen_revision ? (
                          <span className="font-mono text-[10px] text-muted-foreground">
                            Dictamen {d.datos.dictamen_revision}
                          </span>
                        ) : null}
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider leading-none">
                        CIP
                      </div>
                      <div className="font-mono font-bold text-primary tabular-nums leading-tight">
                        {d.delegado.cip ?? "-"}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </DetalleSection>
  );
}
