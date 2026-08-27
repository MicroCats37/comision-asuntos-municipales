"use client";

/**
 * ReciboInspectorCard — Card para mostrar un Recibo de Honorario de Inspector.
 * Muestra: inspector, especialidad, liquidación, detalle de inspecciones y montos.
 */
import { Banknote, FileText, HardHat, Scale } from "lucide-react";
import type { ReciboHonorarioInspector } from "@/features/finanzas/schemas/recibo-honorario.schema";
import {
  formatCurrency,
  formatDate,
} from "@/features/liquidaciones/components/liquidacion-ui";

interface ReciboInspectorCardProps {
  item: ReciboHonorarioInspector;
}

export function ReciboInspectorCard({ item }: ReciboInspectorCardProps) {
  const lg = item.liquidacion_general;
  const insp = item.inspector;
  const esp = item.especialidad;
  const calc = item.calculo;
  const liqEsp = item.liquidacion_especifica;

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-muted/30 border-b border-border">
        <div className="flex items-center gap-2">
          <HardHat className="h-4 w-4 text-muted-foreground" />
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Recibo de Honorario - Inspector
          </span>
        </div>
        <span className="text-xs text-muted-foreground">
          {formatDate(item.created_at)}
        </span>
      </div>

      <div className="p-4 space-y-4">
        {/* Inspector + Especialidad */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="flex items-start gap-3 p-3 rounded-lg border border-border/60 bg-muted/10">
            <div className="p-2 bg-primary/10 rounded-lg shrink-0">
              <HardHat className="h-4 w-4 text-primary" />
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
              <p className="text-[10px] text-muted-foreground">
                Revisión / Liq
              </p>
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

        {/* Detalle de inspecciones */}
        <div className="p-3 rounded-lg border border-border/60 bg-muted/10">
          <div className="flex items-center gap-2 mb-3">
            <HardHat className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
              Inspecciones
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div>
              <p className="text-[10px] text-muted-foreground">Programadas</p>
              <p className="text-sm font-semibold">
                {calc.inspecciones_programadas}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">Del Mes</p>
              <p className="text-sm font-semibold text-primary">
                {calc.inspecciones_mes}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">Pagadas</p>
              <p className="text-sm font-semibold">
                {calc.inspecciones_pagadas}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">Saldo</p>
              <p className="text-sm font-semibold">{calc.saldo_inspecciones}</p>
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
              <p className="text-[10px] text-muted-foreground">
                Costo / Inspección
              </p>
              <p className="text-sm font-semibold">
                {formatCurrency(calc.costo_por_inspeccion)}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">Monto Bruto</p>
              <p className="text-sm font-semibold">
                {formatCurrency(calc.monto_bruto)}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">Sub Total</p>
              <p className="text-sm font-semibold">
                {formatCurrency(calc.sub_total)}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">
                Descuento ({(calc.tasa_descuento_aplicada * 100).toFixed(0)}%)
              </p>
              <p className="text-sm font-semibold text-destructive/80">
                -{formatCurrency(calc.descuento)}
              </p>
            </div>
            <div className="col-span-2 sm:col-span-2">
              <p className="text-[10px] text-muted-foreground">
                Honorarios a Pagar
              </p>
              <p className="text-base font-bold text-primary">
                {formatCurrency(calc.honorarios)}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
