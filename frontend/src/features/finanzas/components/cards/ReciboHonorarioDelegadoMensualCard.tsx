"use client";

/**
 * ReciboHonorarioDelegadoMensualCard — Card para mostrar una liquidacion de honorarios
 * Mensual del delegado.
 * Muestra: Periodo, Delegado, Neto a Pagar, número de liquidaciones y expedientes.
 */
import { Banknote, Calendar, FileText, Printer, User } from "lucide-react";
import type { ReciboHonorarioDelegadoMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";
import {
  formatCurrency,
  formatDate,
} from "@/features/liquidaciones/components/liquidacion-ui";
import { RhDelegadoVariablesCalculo } from "@/features/finanzas/components/RhDelegadoVariablesCalculo";
import { printRhDelegadoMensual } from "@/features/finanzas/pdf/printRhDelegadoMensual";

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
  const vc = item.variables_calculo;
  const pctRenta =
    vc?.tasa_renta_cip != null ? (vc.tasa_renta_cip * 100).toFixed(0) : null;
  const pctAporte =
    vc?.tasa_aporte_codemu != null
      ? (vc.tasa_aporte_codemu * 100).toFixed(0)
      : null;
  const pctFondo =
    vc?.tasa_fondo_comun != null
      ? (vc.tasa_fondo_comun * 100).toFixed(0)
      : null;

  const handlePrint = () => {
    printRhDelegadoMensual(item);
  };

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-muted/30 border-b border-border">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground" />
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            Liquidacion de Honorarios Mensual
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Calendar className="h-3.5 w-3.5" />
            <span>{formatDate(item.fecha_registro)}</span>
          </div>
          <button
            onClick={handlePrint}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
            title="Imprimir"
          >
            <Printer className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Periodo + Delegado + Operatividad */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="flex items-start gap-3 p-3 rounded-lg border border-border/60 bg-muted/10">
            <div className="p-2 bg-primary/10 rounded-lg shrink-0">
              <Calendar className="h-4 w-4 text-primary" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Periodo
              </p>
              <p className="text-sm font-bold truncate">
                {item.periodo != null && item.mes != null
                  ? `${item.periodo}-${String(item.mes).padStart(2, "0")}`
                  : "—"}
              </p>
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

          {item.delegado_operacion_context ? (
            <div className="flex items-start gap-3 p-3 rounded-lg border border-border/60 bg-green-50/50">
              <div className="p-2 bg-green-100 rounded-lg shrink-0">
                <Banknote className="h-4 w-4 text-green-700" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                  Operatividad
                </p>
                <p
                  className="text-sm font-bold truncate text-green-800"
                  title={item.delegado_operacion_context.municipalidad_nombre}
                >
                  {item.delegado_operacion_context.municipalidad_nombre}
                </p>
                <div className="flex flex-wrap gap-1 mt-0.5">
                  {item.delegado_operacion_context.tipo_liquidacion_nombre && (
                    <span className="inline-flex items-center rounded bg-green-200 px-1.5 py-0.5 text-[10px] font-semibold text-green-800">
                      {item.delegado_operacion_context.tipo_liquidacion_nombre}
                    </span>
                  )}
                  <span className="inline-flex items-center rounded bg-green-200 px-1.5 py-0.5 text-[10px] font-semibold text-green-800">
                    {item.delegado_operacion_context.especialidad_nombre}
                  </span>
                  <span className="inline-flex items-center rounded bg-green-100 px-1.5 py-0.5 text-[10px] font-medium text-green-700 border border-green-300">
                    {item.delegado_operacion_context.tipo}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-3 p-3 rounded-lg border border-border/60 bg-muted/5">
              <div className="p-2 bg-muted rounded-lg shrink-0">
                <Banknote className="h-4 w-4 text-muted-foreground" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                  Operatividad
                </p>
                <p className="text-sm text-muted-foreground italic truncate">
                  Sin operatividad
                </p>
                <p className="text-[10px] text-muted-foreground italic">
                  Flujo legacy
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Detalle de Liquidaciones — tabla compacta */}
        <div className="rounded-lg border border-border/60 overflow-hidden">
          <div className="flex items-center gap-2 px-3 py-2 bg-muted/30 border-b border-border">
            <FileText className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
              Detalle de Liquidaciones
            </span>
            <span className="ml-auto text-xs font-semibold text-primary">
              {liquidacionesCount}{" "}
              {liquidacionesCount === 1 ? "liquidación" : "liquidaciones"}
            </span>
          </div>
          {detalles.length > 0 ? (
            <div className="overflow-x-auto max-h-64">
              <table className="w-full text-[10px] border-collapse">
                <thead className="bg-muted/40 sticky top-0">
                  <tr>
                    <th className="border-b border-border px-1.5 py-1.5 text-left font-bold uppercase tracking-wide text-muted-foreground">
                      Liq
                    </th>
                    <th className="border-b border-border px-1.5 py-1.5 text-left font-bold uppercase tracking-wide text-muted-foreground">
                      F. Rev.
                    </th>
                    <th className="border-b border-border px-1.5 py-1.5 text-left font-bold uppercase tracking-wide text-muted-foreground">
                      Expediente
                    </th>
                    <th className="border-b border-border px-1.5 py-1.5 text-center font-bold uppercase tracking-wide text-muted-foreground">
                      Nro Rev
                    </th>
                    <th className="border-b border-border px-1.5 py-1.5 text-right font-bold uppercase tracking-wide text-muted-foreground">
                      Total
                    </th>
                    <th className="border-b border-border px-1.5 py-1.5 text-right font-bold uppercase tracking-wide text-muted-foreground">
                      Sub Total
                    </th>
                    <th className="border-b border-border px-1.5 py-1.5 text-right font-bold uppercase tracking-wide text-muted-foreground">
                      Imp. Bruto
                    </th>
                    <th className="border-b border-border px-1.5 py-1.5 text-right font-bold uppercase tracking-wide text-muted-foreground">
                      CIP{pctRenta != null ? ` (${pctRenta}%)` : ""}
                    </th>
                    <th className="border-b border-border px-1.5 py-1.5 text-right font-bold uppercase tracking-wide text-muted-foreground">
                      Aporte CODEMU{pctAporte != null ? ` (${pctAporte}%)` : ""}
                    </th>
                    <th className="border-b border-border px-1.5 py-1.5 text-right font-bold uppercase tracking-wide text-muted-foreground">
                      Fondo común{pctFondo != null ? ` (${pctFondo}%)` : ""}
                    </th>
                    <th className="border-b border-border px-1.5 py-1.5 text-right font-bold uppercase tracking-wide text-muted-foreground">
                      Neto Honorario
                    </th>
                    <th className="border-b border-border px-1.5 py-1.5 text-center font-bold uppercase tracking-wide text-muted-foreground">
                      Nro RH
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {detalles.map((detalle, index) => (
                    <tr
                      key={detalle.liquidacion_delegado_id ?? index}
                      className="hover:bg-muted/30"
                    >
                      <td className="border-b border-border/50 px-1.5 py-1 text-center">
                        {index + 1}
                      </td>
                      <td className="border-b border-border/50 px-1.5 py-1">
                        {detalle.fecha_revision
                          ? formatDate(detalle.fecha_revision)
                          : "—"}
                      </td>
                      <td className="border-b border-border/50 px-1.5 py-1 font-mono font-medium">
                        {detalle.expediente || "—"}
                      </td>
                      <td className="border-b border-border/50 px-1.5 py-1 text-center">
                        {detalle.numero_revision ?? "—"}
                      </td>
                      <td className="border-b border-border/50 px-1.5 py-1 text-right">
                        {detalle.total_liquidacion != null
                          ? formatCurrency(detalle.total_liquidacion)
                          : "—"}
                      </td>
                      <td className="border-b border-border/50 px-1.5 py-1 text-right">
                        {detalle.sub_total_liquidacion != null
                          ? formatCurrency(detalle.sub_total_liquidacion)
                          : "—"}
                      </td>
                      <td className="border-b border-border/50 px-1.5 py-1 text-right">
                        {detalle.imp_bruto != null
                          ? formatCurrency(detalle.imp_bruto)
                          : "—"}
                      </td>
                      <td className="border-b border-border/50 px-1.5 py-1 text-right text-destructive">
                        {detalle.renta_cip != null
                          ? `- ${formatCurrency(detalle.renta_cip)}`
                          : "—"}
                      </td>
                      <td className="border-b border-border/50 px-1.5 py-1 text-right text-destructive">
                        {detalle.aporte_codemu != null
                          ? `- ${formatCurrency(detalle.aporte_codemu)}`
                          : "—"}
                      </td>
                      <td className="border-b border-border/50 px-1.5 py-1 text-right text-destructive">
                        {detalle.fondo_comun != null
                          ? `- ${formatCurrency(detalle.fondo_comun)}`
                          : "—"}
                      </td>
                      <td className="border-b border-border/50 px-1.5 py-1 text-right font-semibold">
                        {detalle.neto_honorario != null
                          ? formatCurrency(detalle.neto_honorario)
                          : "—"}
                      </td>
                      <td className="border-b border-border/50 px-1.5 py-1 text-center">
                        {detalle.numero_rh ?? "—"}
                      </td>
                    </tr>
                  ))}
                  {/* Fila de Totales */}
                  <tr className="bg-muted/50 font-semibold">
                    <td
                      colSpan={4}
                      className="border-b border-border px-1.5 py-1.5 text-center uppercase tracking-wide"
                    >
                      Totales
                    </td>
                    <td className="border-b border-border px-1.5 py-1.5 text-right">
                      {formatCurrency(
                        detalles.reduce(
                          (sum, d) => sum + (d.total_liquidacion ?? 0),
                          0,
                        ),
                      )}
                    </td>
                    <td className="border-b border-border px-1.5 py-1.5 text-right">
                      {formatCurrency(
                        detalles.reduce(
                          (sum, d) => sum + (d.sub_total_liquidacion ?? 0),
                          0,
                        ),
                      )}
                    </td>
                    <td className="border-b border-border px-1.5 py-1.5 text-right">
                      {formatCurrency(
                        detalles.reduce(
                          (sum, d) => sum + (d.imp_bruto ?? 0),
                          0,
                        ),
                      )}
                    </td>
                    <td className="border-b border-border px-1.5 py-1.5 text-right text-destructive">
                      - {formatCurrency(totales.renta_cip)}
                    </td>
                    <td className="border-b border-border px-1.5 py-1.5 text-right text-destructive">
                      - {formatCurrency(totales.aporte_codemu)}
                    </td>
                    <td className="border-b border-border px-1.5 py-1.5 text-right text-destructive">
                      - {formatCurrency(totales.fondo_comun)}
                    </td>
                    <td className="border-b border-border px-1.5 py-1.5 text-right font-black text-primary">
                      {formatCurrency(totales.neto_honorario)}
                    </td>
                    <td className="border-b border-border px-1.5 py-1" />
                  </tr>
                </tbody>
              </table>
            </div>
          ) : (
            <div className="px-3 py-4 text-xs text-muted-foreground italic text-center">
              Sin liquidaciones asociadas
            </div>
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
                CIP{pctRenta != null ? ` (${pctRenta}%)` : ""}
              </p>
              <p className="text-sm font-semibold text-destructive/80">
                -{formatCurrency(totales.renta_cip)}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">
                Aporte CODEMU{pctAporte != null ? ` (${pctAporte}%)` : ""}
              </p>
              <p className="text-sm font-semibold text-destructive/80">
                -{formatCurrency(totales.aporte_codemu)}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-muted-foreground">
                Fondo común{pctFondo != null ? ` (${pctFondo}%)` : ""}
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
          {/* Tasas aplicadas — compact row */}
          {item.variables_calculo && (
            <RhDelegadoVariablesCalculo
              tasa_renta_cip={item.variables_calculo.tasa_renta_cip}
              tasa_aporte_codemu={item.variables_calculo.tasa_aporte_codemu}
              tasa_fondo_comun={item.variables_calculo.tasa_fondo_comun}
              compact
            />
          )}
        </div>
      </div>
    </div>
  );
}
