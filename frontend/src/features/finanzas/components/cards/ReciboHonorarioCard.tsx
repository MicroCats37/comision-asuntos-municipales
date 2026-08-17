"use client";

/**
 * ReciboHonorarioCard — Card para mostrar un Recibo de Honorario.
 * Muestra: delegado, especialidad, liquidación, montos.
 */
import { Banknote, FileText, Scale, User } from "lucide-react";
import type { ReciboHonorarioDelegado } from "@/features/finanzas/schemas/recibo-honorario.schema";
import {
  formatCurrency,
  formatDate,
} from "@/features/liquidaciones/components/liquidacion-ui";

interface ReciboHonorarioCardProps {
  item: ReciboHonorarioDelegado;
}

export function ReciboHonorarioCard({ item }: ReciboHonorarioCardProps) {
  const lg = item.liquidacion_general;
  const del = item.delegado;
  const esp = item.especialidad;
  const calc = item.calculo;
  const liqEsp = item.liquidacion_especifica;

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-muted/30 border-b border-border">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground" />
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Recibo de Honorario
          </span>
        </div>
        <span className="text-xs text-muted-foreground">
          {formatDate(item.created_at)}
        </span>
      </div>

      <div className="p-4 space-y-4">
        {/* Delegado + Especialidad */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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

          <div className="flex items-start gap-3 p-3 rounded-lg border border-border/60 bg-muted/10">
            <div className="p-2 bg-primary/10 rounded-lg shrink-0">
              <Scale className="h-4 w-4 text-primary" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Especialidad
              </p>
              <p className="text-sm font-semibold truncate">
                {esp?.nombre ?? "—"}
              </p>
              <p className="text-xs text-muted-foreground">
                Código: {esp?.codigo ?? "—"}
              </p>
            </div>
          </div>
        </div>

        {/* Liquidación */}
        <div className="p-3 rounded-lg border border-border/60 bg-muted/10">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
              Liquidación
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div>
              <p className="text-[10px] text-muted-foreground">Expediente</p>
              <p className="text-sm font-medium truncate">
                {lg?.expediente ?? "—"}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">Revisión / Liq</p>
              <p className="text-sm font-medium">
                N° {lg?.numero_revision ?? "—"} / #{liqEsp?.numero ?? "—"}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">Tipo</p>
              <p className="text-sm font-medium truncate">
                {lg?.tipo_liquidacion?.nombre ?? "—"}
              </p>
            </div>
            <div className="col-span-2 sm:col-span-1">
              <p className="text-[10px] text-muted-foreground">Municipalidad</p>
              <p className="text-sm font-medium truncate">
                {lg?.municipalidad_nombre ?? "—"}
              </p>
            </div>
            <div className="col-span-2">
              <p className="text-[10px] text-muted-foreground">Proyecto</p>
              <p className="text-sm font-medium truncate">
                {lg?.proyecto_denominacion ?? "—"}
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
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div>
              <p className="text-[10px] text-muted-foreground">Importe Bruto</p>
              <p className="text-sm font-semibold">
                {formatCurrency(calc.imp_bruto)}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">
                Renta CIP (25%)
              </p>
              <p className="text-sm font-semibold text-destructive/80">
                -{formatCurrency(calc.renta_cip)}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">
                Aporte CODEMU (5%)
              </p>
              <p className="text-sm font-semibold text-destructive/80">
                -{formatCurrency(calc.aporte_codemu)}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">
                Fondo Común (10%)
              </p>
              <p className="text-sm font-semibold text-destructive/80">
                -{formatCurrency(calc.fondo_comun)}
              </p>
            </div>
            <div className="col-span-2 sm:col-span-1">
              <p className="text-[10px] text-muted-foreground">
                Neto Honorario
              </p>
              <p className="text-base font-bold text-primary">
                {formatCurrency(calc.neto_honorario)}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
