"use client";

import { ClipboardCheck, Receipt, User } from "lucide-react";
import type {
  RegistroPagoOut,
  VisitasDatosOut,
} from "../../schemas/liquidacion-visitas.schema";
import { formatCurrency, formatEnumLabel } from "../liquidacion-ui";
import { TarifaDetailSection, type TarifaParam } from "./TarifaDetailSection";

interface Props {
  liquidacionTipo: VisitasDatosOut;
  /** Valor del UIT vigente de la liquidación (`liquidacion_general.uit.valor`).
   *  Necesario para derivar el costo por visita: UIT × porcentaje_uit. */
  uit?: number | null;
}

/**
 * Inspección de Obra-specific (Visitas) param block + inspectores +
 * registros de pago tables. Uses the shared `TarifaDetailSection` wrapper
 * for the params grid; renders the inspectores and registros_pago tables
 * via the `children` slot.
 *
 * Note: IO does NOT use delegados (uses inspectores instead). That's why
 * this section is more compact than the PorcentajeObra variants.
 */
export function LiquidacionDetalleInspeccionObraSection({
  liquidacionTipo: lt,
  uit,
}: Props) {
  // Costo por visita = UIT × porcentaje_uit (porcentaje_uit ya es fracción).
  const costoPorVisita =
    uit != null && lt.porcentaje_uit != null ? uit * lt.porcentaje_uit : null;

  const params: TarifaParam[] = [
    {
      label: "Categoría",
      value: (
        <span className="inline-flex items-center rounded bg-secondary px-1.5 py-0.5 text-xs font-bold uppercase tracking-wider text-secondary-foreground">
          {formatEnumLabel(lt.categoria) ?? "—"}
        </span>
      ),
    },
    {
      label: "Cant. Visitas",
      value: <span className="tabular-nums">{lt.cantidad_visitas ?? 0}</span>,
    },
    {
      label: "% UIT",
      value: (
        <span className="font-mono font-bold text-primary tabular-nums">
          {lt.porcentaje_uit?.toLocaleString("es-PE", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 4,
          }) ?? "—"}
          %
        </span>
      ),
    },
    ...(costoPorVisita != null
      ? [
          {
            label: "Costo / Visita",
            value: (
              <span className="font-bold text-primary tabular-nums">
                {formatCurrency(costoPorVisita)}
              </span>
            ),
          },
        ]
      : []),
  ];

  const inspectoresCount = lt.inspectores?.length ?? 0;
  const registrosCount = lt.registros_pago?.length ?? 0;

  return (
    <TarifaDetailSection
      title="Detalle técnico de Inspección de Obra"
      icon={ClipboardCheck}
      params={params}
      emptyText="Sin parámetros de visitas registrados."
    >
      {/* Inspectores table */}
      <div className="rounded-lg border border-border/50 bg-card overflow-hidden">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-border/40 bg-muted/20">
          <User className="h-3 w-3 text-muted-foreground/70" />
          <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
            Inspectores asignados
          </h4>
          <span className="ml-1 inline-flex items-center justify-center h-3.5 w-3.5 rounded-full bg-muted text-[9px] font-bold text-muted-foreground">
            {inspectoresCount}
          </span>
        </div>
        {inspectoresCount > 0 ? (
          <div className="divide-y divide-border/20">
            <div className="grid grid-cols-[1fr_auto_auto] gap-x-4 px-3 py-1.5 bg-muted/15 min-w-0">
              <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider">
                Nombre
              </span>
              <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider text-right min-w-[4rem]">
                CIP
              </span>
              <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider text-right min-w-[5rem]">
                Categoría
              </span>
            </div>
            {lt.inspectores?.map((inspector) => (
              <div
                key={inspector.id}
                className="grid grid-cols-[1fr_auto_auto] gap-x-4 px-3 py-2 hover:bg-muted/8 transition-colors min-w-0"
              >
                <span className="text-xs text-foreground truncate">
                  {inspector.perfil_ingeniero.nombre_completo}
                </span>
                <span className="text-xs font-medium text-primary text-right min-w-[4rem]">
                  {inspector.perfil_ingeniero.cip}
                </span>
                <span className="text-xs text-muted-foreground text-right min-w-[5rem]">
                  {inspector.categoria ?? lt.categoria ?? "—"}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="px-3 py-2 text-xs text-muted-foreground/60 italic">
            Sin inspectores asignados
          </p>
        )}
      </div>

      {/* Registros de pago table */}
      <div className="rounded-lg border border-border/50 bg-card overflow-hidden">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-border/40 bg-muted/20">
          <Receipt className="h-3 w-3 text-muted-foreground/70" />
          <h4 className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
            Registros de pago
          </h4>
          <span className="ml-1 inline-flex items-center justify-center h-3.5 w-3.5 rounded-full bg-muted text-[9px] font-bold text-muted-foreground">
            {registrosCount}
          </span>
        </div>
        {registrosCount > 0 ? (
          <div className="divide-y divide-border/20">
            <div className="grid grid-cols-[auto_auto_1fr_auto] gap-x-4 px-3 py-1.5 bg-muted/15 min-w-0">
              <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider min-w-[3.5rem]">
                Periodo
              </span>
              <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider min-w-[3.5rem]">
                Mes
              </span>
              <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider">
                Inspecciones pagadas
              </span>
              <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider text-right min-w-[5rem]">
                Fecha registro
              </span>
            </div>
            {(
              [...(lt.registros_pago ?? [])].sort((a, b) => {
                const dateA = a.fecha_registro
                  ? new Date(a.fecha_registro).getTime()
                  : 0;
                const dateB = b.fecha_registro
                  ? new Date(b.fecha_registro).getTime()
                  : 0;
                return dateB - dateA;
              }) as RegistroPagoOut[]
            ).map((registro) => (
              <div
                key={registro.id}
                className="grid grid-cols-[auto_auto_1fr_auto] gap-x-4 px-3 py-2 hover:bg-muted/8 transition-colors min-w-0"
              >
                <span className="text-xs text-foreground min-w-[3.5rem]">
                  {registro.periodo ?? "—"}
                </span>
                <span className="text-xs text-foreground min-w-[3.5rem]">
                  {registro.mes ?? "—"}
                </span>
                <span className="text-xs font-medium text-primary">
                  {registro.inspecciones_pagadas ?? 0}
                </span>
                <span className="text-xs text-muted-foreground text-right min-w-[5rem]">
                  {registro.fecha_registro
                    ? new Date(registro.fecha_registro).toLocaleDateString(
                        "es-PE",
                        {
                          day: "2-digit",
                          month: "2-digit",
                          year: "numeric",
                        },
                      )
                    : "—"}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="px-3 py-2 text-xs text-muted-foreground/60 italic">
            Sin registros de pago
          </p>
        )}
      </div>
    </TarifaDetailSection>
  );
}
