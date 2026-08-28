"use client";

/**
 * ReciboHonorarioDelegadoMensualCard — Card para mostrar un Recibo de Honorario
 * Mensual del delegado.
 * Muestra: Periodo, Delegado, Neto a Pagar, número de liquidaciones y expedientes.
 */
import { Banknote, Calendar, FileText, User } from "lucide-react";
import type { ReciboHonorarioDelegadoMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";
import {
  formatCurrency,
  formatDate,
} from "@/features/liquidaciones/components/liquidacion-ui";

interface ReciboHonorarioDelegadoMensualCardProps {
  item: ReciboHonorarioDelegadoMensual;
}

export function ReciboHonorarioDelegadoMensualCard({
  item,
}: ReciboHonorarioDelegadoMensualCardProps) {
  const del = item.delegado;
  const totales = item.totales;
  const detalles = item.detalles || [];
  const liquidacionesCount = detalles.length;

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-muted/30 border-b border-border">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground" />
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Recibo de Honorario Mensual
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Calendar className="h-3.5 w-3.5" />
          <span>{formatDate(item.fecha_registro)}</span>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Periodo + Delegado */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="flex items-start gap-3 p-3 rounded-lg border border-border/60 bg-muted/10">
            <div className="p-2 bg-primary/10 rounded-lg shrink-0">
              <Calendar className="h-4 w-4 text-primary" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Periodo
              </p>
              <p className="text-sm font-bold truncate">{item.periodo}</p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-3 rounded-lg border border-border/60 bg-muted/10">
            <div className="p-2 bg-primary/10 rounded-lg shrink-0">
              <User className="h-4 w-4 text-primary" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Delegado
              </p>
              <p className="text-sm font-semibold truncate">
                {del?.nombre_completo ?? "—"}
              </p>
              <p className="text-xs text-muted-foreground">
                CIP: {del?.cip ?? "—"}
              </p>
            </div>
          </div>
        </div>

        {/* Liquidaciones incluidas */}
        <div className="p-3 rounded-lg border border-border/60 bg-muted/10">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
              Liquidaciones incluidas
            </span>
            <span className="ml-auto text-xs font-semibold text-primary">
              {liquidacionesCount}{" "}
              {liquidacionesCount === 1 ? "liquidación" : "liquidaciones"}
            </span>
          </div>
          {detalles.length > 0 ? (
            <div className="space-y-1.5">
              {detalles.slice(0, 5).map((detalle, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between text-xs"
                >
                  <span className="text-muted-foreground truncate max-w-[60%]">
                    {detalle.expediente || "—"}
                  </span>
                  <span className="font-medium ml-2">
                    {formatCurrency(detalle.imp_bruto)}
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
              Sin liquidaciones asociadas
            </p>
          )}
        </div>

        {/* Montos */}
        <div className="p-3 rounded-lg border border-border/60 bg-muted/10">
          <div className="flex items-center gap-2 mb-3">
            <Banknote className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
              Detalle de Montos
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div>
              <p className="text-[10px] text-muted-foreground">Sub Total</p>
              <p className="text-sm font-semibold">
                {formatCurrency(totales.sub_total)}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">
                Renta CIP (25%)
              </p>
              <p className="text-sm font-semibold text-destructive/80">
                -{formatCurrency(totales.renta_cip)}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">
                Aporte CODEMU (5%)
              </p>
              <p className="text-sm font-semibold text-destructive/80">
                -{formatCurrency(totales.aporte_codemu)}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">
                Fondo Común (10%)
              </p>
              <p className="text-sm font-semibold text-destructive/80">
                -{formatCurrency(totales.fondo_comun)}
              </p>
            </div>
            <div className="col-span-2 sm:col-span-1">
              <p className="text-[10px] text-muted-foreground">Neto a Pagar</p>
              <p className="text-base font-bold text-primary">
                {formatCurrency(totales.neto_honorario)}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
