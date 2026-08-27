"use client";

/**
 * ReciboHonorarioInspectorMensualCard — Card para mostrar un Recibo de Honorario
 * Mensual del inspector.
 * Muestra: Periodo, Inspector, Totales, número de IO y detalle de inspecciones.
 */
import { Banknote, Calendar, FileText, User } from "lucide-react";
import type { ReciboHonorarioInspectorMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";
import {
  formatCurrency,
  formatDate,
} from "@/features/liquidaciones/components/liquidacion-ui";

interface ReciboHonorarioInspectorMensualCardProps {
  item: ReciboHonorarioInspectorMensual;
}

export function ReciboHonorarioInspectorMensualCard({
  item,
}: ReciboHonorarioInspectorMensualCardProps) {
  const insp = item.inspector;
  const totales = item.totales;
  const detalles = item.detalles || [];
  const ioCount = detalles.length;

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-muted/30 border-b border-border">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground" />
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Recibo de Honorario Mensual — Inspector
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Calendar className="h-3.5 w-3.5" />
          <span>{formatDate(item.fecha_registro)}</span>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Periodo + Inspector */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="flex items-start gap-3 p-3 rounded-lg border border-border/60 bg-muted/10">
            <div className="p-2 bg-blue-500/10 rounded-lg shrink-0">
              <Calendar className="h-4 w-4 text-blue-600" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Periodo
              </p>
              <p className="text-sm font-bold truncate">{item.periodo}</p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 rounded-lg border border-border/60 bg-muted/10">
            <div className="p-2 bg-blue-500/10 rounded-lg shrink-0">
              <User className="h-4 w-4 text-blue-600" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Inspector
              </p>
              <p className="text-sm font-semibold truncate">
                {insp?.nombre_completo ?? "—"}
              </p>
              <p className="text-xs text-muted-foreground">
                CIP: {insp?.cip ?? "—"}
              </p>
            </div>
          </div>
        </div>

        {/* IO incluidas */}
        <div className="p-3 rounded-lg border border-border/60 bg-muted/10">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
              Inspecciones de Obra (IO) incluidas
            </span>
            <span className="ml-auto text-xs font-semibold text-primary">
              {ioCount} {ioCount === 1 ? "IO" : "IOs"}
            </span>
          </div>
          {detalles.length > 0 ? (
            <div className="space-y-1.5">
              {detalles.slice(0, 5).map((detalle, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between text-xs"
                >
                  <span className="text-muted-foreground truncate max-w-[50%]">
                    {detalle.expediente || "—"}
                  </span>
                  <span className="text-muted-foreground truncate max-w-[30%] ml-2">
                    {detalle.nombre_propietario || "—"}
                  </span>
                  <span className="font-medium ml-2">
                    {detalle.inspecciones_liquidadas} insp.
                  </span>
                  <span className="font-medium text-primary ml-2">
                    {formatCurrency(detalle.monto_contribuido)}
                  </span>
                </div>
              ))}
              {detalles.length > 5 && (
                <p className="text-[10px] text-muted-foreground text-center">
                  +{detalles.length - 5} más
                </p>
              )}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground italic">
              Sin IO asociadas
            </p>
          )}
        </div>

        {/* Totales de Inspecciones */}
        <div className="p-3 rounded-lg border border-border/60 bg-muted/10">
          <div className="flex items-center gap-2 mb-3">
            <Banknote className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
              Resumen de Inspecciones
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div>
              <p className="text-[10px] text-muted-foreground">Programadas</p>
              <p className="text-sm font-semibold">
                {totales.inspecciones_programadas}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">Del Mes</p>
              <p className="text-sm font-semibold text-primary">
                {totales.inspecciones_liquidadas}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">Pagadas Anter.</p>
              <p className="text-sm font-semibold text-muted-foreground">
                {totales.inspecciones_pagadas_hasta_mes_anterior}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">Saldo Rest.</p>
              <p className="text-sm font-semibold">
                {totales.saldo_restante}
              </p>
            </div>
          </div>
        </div>

        {/* Montos */}
        <div className="p-3 rounded-lg border border-border/60 bg-muted/10">
          <div className="flex items-center gap-2 mb-3">
            <Banknote className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
              Detalle de Montos
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div>
              <p className="text-[10px] text-muted-foreground">Sub Total</p>
              <p className="text-sm font-semibold">
                {formatCurrency(totales.sub_total)}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">
                Descuento ({totales.tasa_descuento_aplicada * 100}%)
              </p>
              <p className="text-sm font-semibold text-destructive/80">
                -{formatCurrency(totales.descuento)}
              </p>
            </div>
            <div className="col-span-2 sm:col-span-2">
              <p className="text-[10px] text-muted-foreground">
                Neto a Pagar
              </p>
              <p className="text-base font-bold text-primary">
                {formatCurrency(totales.honorarios)}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
