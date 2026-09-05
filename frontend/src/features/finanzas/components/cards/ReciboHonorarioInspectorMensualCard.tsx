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
import { RhInspectorVariablesCalculo } from "@/features/finanzas/components/RhInspectorVariablesCalculo";

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

        {/* IO incluidas — compact table */}
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
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border/50">
                    <th className="text-left text-[10px] font-semibold text-muted-foreground uppercase tracking-wider pb-1.5 pr-3 whitespace-nowrap">
                      N° Liq.
                    </th>
                    <th className="text-left text-[10px] font-semibold text-muted-foreground uppercase tracking-wider pb-1.5 pr-3 whitespace-nowrap">
                      Expediente
                    </th>
                    <th className="text-left text-[10px] font-semibold text-muted-foreground uppercase tracking-wider pb-1.5 px-3 whitespace-nowrap">
                      Administrado
                    </th>
                    <th className="text-left text-[10px] font-semibold text-muted-foreground uppercase tracking-wider pb-1.5 px-3 whitespace-nowrap">
                      Distrito
                    </th>
                    <th className="text-right text-[10px] font-semibold text-muted-foreground uppercase tracking-wider pb-1.5 px-3 whitespace-nowrap">
                      Prog.
                    </th>
                    <th className="text-right text-[10px] font-semibold text-muted-foreground uppercase tracking-wider pb-1.5 px-3 whitespace-nowrap">
                      Liq.
                    </th>
                    <th className="text-right text-[10px] font-semibold text-muted-foreground uppercase tracking-wider pb-1.5 px-3 whitespace-nowrap">
                      Pag. Ant.
                    </th>
                    <th className="text-right text-[10px] font-semibold text-muted-foreground uppercase tracking-wider pb-1.5 px-3 whitespace-nowrap">
                      Saldo
                    </th>
                    <th className="text-left text-[10px] font-semibold text-muted-foreground uppercase tracking-wider pb-1.5 px-3 whitespace-nowrap">
                      Comprobante
                    </th>
                    <th className="text-right text-[10px] font-semibold text-muted-foreground uppercase tracking-wider pb-1.5 pl-3 whitespace-nowrap">
                      Costo/Und.
                    </th>
                    <th className="text-right text-[10px] font-semibold text-muted-foreground uppercase tracking-wider pb-1.5 pl-3 whitespace-nowrap">
                      Monto
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {detalles.map((detalle, i) => {
                    const comp = detalle.comprobante_activo;
                    const compLabel = comp
                      ? `${comp.tipo_comprobante ?? ""} ${comp.serie ?? ""}${comp.numero ?? ""}`.trim()
                      : null;
                    return (
                    <tr
                      key={`${detalle.expediente}-${i}`}
                      className="border-b border-border/30 last:border-b-0 hover:bg-muted/20 transition-colors"
                    >
                      <td className="py-1.5 pr-3 text-muted-foreground text-center whitespace-nowrap font-mono text-[10px]">
                        {detalle.liquidacion_especifica_numero ?? "—"}
                      </td>
                      <td className="py-1.5 pr-3 text-muted-foreground truncate max-w-[100px]">
                        {detalle.expediente || "—"}
                      </td>
                      <td className="py-1.5 px-3 text-muted-foreground truncate max-w-[140px]">
                        {detalle.nombre_propietario || "—"}
                      </td>
                      <td className="py-1.5 px-3 text-muted-foreground truncate max-w-[110px]">
                        {detalle.distrito ?? "—"}
                      </td>
                      <td className="py-1.5 px-3 text-right font-medium whitespace-nowrap">
                        {detalle.inspecciones_programadas}
                      </td>
                      <td className="py-1.5 px-3 text-right font-medium text-primary whitespace-nowrap">
                        {detalle.inspecciones_liquidadas}
                      </td>
                      <td className="py-1.5 px-3 text-right text-muted-foreground whitespace-nowrap">
                        {detalle.inspecciones_pagadas_hasta_mes_anterior}
                      </td>
                      <td className="py-1.5 px-3 text-right font-medium whitespace-nowrap">
                        {detalle.saldo_restante}
                      </td>
                      <td className="py-1.5 px-3 text-muted-foreground truncate max-w-[120px] text-[10px]">
                        {compLabel ?? "—"}
                      </td>
                      <td className="py-1.5 pl-3 text-right text-muted-foreground whitespace-nowrap">
                        {formatCurrency(detalle.costo_por_inspeccion)}
                      </td>
                      <td className="py-1.5 pl-3 text-right font-semibold text-primary whitespace-nowrap">
                        {formatCurrency(detalle.monto_contribuido)}
                      </td>
                    </tr>
                  );})}
                </tbody>
                {/* Totals row */}
                <tfoot>
                  <tr className="border-t border-border/50 bg-muted/20">
                    <td
                      colSpan={7}
                      className="py-1.5 pr-3 text-[10px] font-bold text-muted-foreground uppercase tracking-wider"
                    >
                      TOTALES
                    </td>
                    <td className="py-1.5 px-3 text-right font-medium whitespace-nowrap">
                      {totales.saldo_restante}
                    </td>
                    <td className="py-1.5 px-3 text-muted-foreground" />
                    <td className="py-1.5 pl-3 text-right text-muted-foreground whitespace-nowrap" />
                    <td className="py-1.5 pl-3 text-right font-bold text-primary whitespace-nowrap">
                      {formatCurrency(totales.sub_total)}
                    </td>
                  </tr>
                </tfoot>
              </table>
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
              <p className="text-[10px] text-muted-foreground">
                Pagadas Anter.
              </p>
              <p className="text-sm font-semibold text-muted-foreground">
                {totales.inspecciones_pagadas_hasta_mes_anterior}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">Saldo Rest.</p>
              <p className="text-sm font-semibold">{totales.saldo_restante}</p>
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
                Descuento (
                {item.variables_calculo?.rango_aplicado?.porcentaje_descuento != null
                  ? (item.variables_calculo.rango_aplicado.porcentaje_descuento * 100).toFixed(0)
                  : (totales.tasa_descuento_aplicada * 100).toFixed(0)}
                %)
              </p>
              <p className="text-sm font-semibold text-destructive/80">
                -{formatCurrency(totales.descuento)}
              </p>
            </div>
            <div className="col-span-2 sm:col-span-2">
              <p className="text-[10px] text-muted-foreground">Neto a Pagar</p>
              <p className="text-base font-bold text-primary">
                {formatCurrency(totales.honorarios)}
              </p>
            </div>
          </div>
          {/* Descuento aplicado — compact row */}
          {item.variables_calculo ? (
            <RhInspectorVariablesCalculo
              escala_nombre={item.variables_calculo.escala_nombre}
              porcentaje_descuento={
                item.variables_calculo.rango_aplicado.porcentaje_descuento
              }
              monto_minimo={
                item.variables_calculo.rango_aplicado.monto_minimo ?? undefined
              }
              monto_maximo={
                item.variables_calculo.rango_aplicado.monto_maximo ?? undefined
              }
              compact
            />
          ) : (
            <RhInspectorVariablesCalculo
              porcentaje_descuento={totales.tasa_descuento_aplicada}
              compact
            />
          )}
        </div>
      </div>
    </div>
  );
}
