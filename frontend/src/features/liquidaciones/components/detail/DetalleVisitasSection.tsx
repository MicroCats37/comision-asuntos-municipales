"use client";

import { ClipboardList, UserCog } from "lucide-react";
import type { VisitasDatosOut } from "../../schemas/liquidacion-visitas.schema";
import { DetalleField, DetalleSection } from "./DetalleSection";

interface Props {
  visitas: VisitasDatosOut;
}

/**
 * Tipo-specific section for IO — visitas count + categoría + % UIT
 * + inspectores summary (full list lives in `DetalleDelegadosSection`
 * already, but here we show it briefly so the user sees it in the same
 * area as the visitas info).
 */
export function DetalleVisitasSection({ visitas }: Props) {
  const inspectores = visitas.inspectores ?? [];
  return (
    <DetalleSection
      title="Visitas"
      icon={ClipboardList}
      badge={`${visitas.cantidad_visitas}`}
      className="lg:col-span-12"
    >
      <div className="px-4 py-3 flex flex-col gap-3">
        <div className="flex flex-wrap gap-x-5 gap-y-2">
          <DetalleField label="Cantidad" mono>
            <span className="text-base font-black text-primary tabular-nums leading-tight">
              {visitas.cantidad_visitas}
            </span>
            <span className="text-[10px] font-semibold text-muted-foreground/70 uppercase">
              visitas
            </span>
          </DetalleField>
          <DetalleField label="Categoría">
            <span className="inline-flex items-center rounded bg-secondary px-1.5 py-0.5 text-xs font-bold uppercase tracking-wider text-secondary-foreground">
              {visitas.categoria}
            </span>
          </DetalleField>
          <DetalleField label="% UIT">
            <span className="font-mono font-bold text-primary tabular-nums">
              {visitas.porcentaje_uit?.toLocaleString("es-PE", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 4,
              }) ?? "—"}
              %
            </span>
          </DetalleField>
          {visitas.tarifa_aplicada_id ? (
            <DetalleField label="Tarifa" mono>
              {visitas.tarifa_aplicada_id}
            </DetalleField>
          ) : null}
        </div>

        {inspectores.length > 0 ? (
          <div className="border-t border-border/40 pt-3">
            <div className="flex items-center gap-1.5 mb-1.5">
              <UserCog className="h-3 w-3 text-muted-foreground/60" />
              <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                Inspector asignado
              </span>
            </div>
            <div className="flex flex-col gap-1">
              {inspectores.map((ins, i) => (
                <div
                  key={ins.id ?? `ins-${i}`}
                  className="flex items-baseline gap-1.5 text-xs"
                >
                  <span className="text-foreground/90 font-semibold truncate">
                    {ins.perfil_ingeniero?.nombre_completo ?? "—"}
                  </span>
                  {ins.categoria ? (
                    <span
                      className={
                        "inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider " +
                        (ins.categoria === "TITULAR"
                          ? "bg-primary/10 text-primary"
                          : "bg-secondary text-secondary-foreground/80")
                      }
                    >
                      {ins.categoria}
                    </span>
                  ) : null}
                  {ins.dictamen_revision ? (
                    <span className="font-mono text-[10px] text-muted-foreground/70 italic">
                      Dict. {ins.dictamen_revision}
                    </span>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </DetalleSection>
  );
}
