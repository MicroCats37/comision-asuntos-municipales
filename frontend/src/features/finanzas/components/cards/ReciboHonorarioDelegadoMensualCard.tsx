"use client";

/**
 * ReciboHonorarioDelegadoMensualCard — Card para mostrar un Recibo de Honorario
 * Mensual del delegado.
 *
 * Comparte la ESTRUCTURA, el header, el resumen y las acciones con la card de
 * Inspector a través del shell común `RhMensualCardShell`. Lo específico del
 * dominio —la tabla de liquidaciones (con N° de liquidación, comprobante y N°
 * RH), el bloque de operatividad y las variables de cálculo— se mantiene aquí.
 */
import {
  Banknote,
  FileDown,
  FilePenLine,
  FileText,
  Trash2,
  User,
} from "lucide-react";
import {
  type RhCardAction,
  RhMensualCardShell,
} from "@/features/finanzas/components/cards/RhMensualCardShell";
import { RhDelegadoVariablesCalculo } from "@/features/finanzas/components/RhDelegadoVariablesCalculo";
import { printRhDelegadoMensual } from "@/features/finanzas/pdf/printRhDelegadoMensual";
import type { ReciboHonorarioDelegadoMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";
import {
  formatCurrency,
  formatDate,
} from "@/features/liquidaciones/components/liquidacion-ui";

interface ReciboHonorarioDelegadoMensualCardProps {
  item: ReciboHonorarioDelegadoMensual;
  onDelete?: (id: string) => void;
  /** Abre el modal de RH mensual en modo edición con este recibo. */
  onEdit?: (item: ReciboHonorarioDelegadoMensual) => void;
}

export function ReciboHonorarioDelegadoMensualCard({
  item,
  onDelete,
  onEdit,
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

  const handleDelete = () => {
    onDelete?.(item.id);
  };

  const handleEdit = () => {
    onEdit?.(item);
  };

  /**
   * Acciones del recibo — mismo orden, dimensiones, iconos y política de
   * texto que la card de Inspector (shell común).
   */
  const actions: RhCardAction[] = [
    {
      key: "print",
      icon: <FileDown className="h-3 w-3" />,
      label: "Imprimir",
      ariaLabel: "Imprimir recibo",
      onAction: handlePrint,
    },
  ];

  if (onEdit) {
    actions.push({
      key: "edit",
      icon: <FilePenLine className="h-3 w-3" />,
      label: "Editar",
      ariaLabel: "Editar recibo",
      onAction: handleEdit,
    });
  }

  if (onDelete) {
    actions.push({
      key: "delete",
      icon: <Trash2 className="h-3 w-3" />,
      label: "Eliminar",
      ariaLabel: "Eliminar recibo",
      onAction: handleDelete,
      variant: "danger",
    });
  }

  return (
    <RhMensualCardShell
      kindIcon={User}
      kindLabel="Delegado"
      rhNumero={item.numero}
      fechaRegistro={item.fecha_registro}
      periodo={{ periodo: item.periodo, mes: item.mes }}
      personaNombre={del?.nombre_completo ?? null}
      personaDocumento={del?.cip ? `CIP: ${del.cip}` : null}
      totalLabel="Neto a pagar"
      total={totales.neto_honorario}
      summaryItems={[
        { label: "Subtotal", value: formatCurrency(totales.sub_total) },
        {
          label: `CIP${pctRenta != null ? ` (${pctRenta}%)` : ""}`,
          value: `- ${formatCurrency(totales.renta_cip)}`,
          tone: "danger",
        },
        {
          label: `Aporte CODEMU${pctAporte != null ? ` (${pctAporte}%)` : ""}`,
          value: `- ${formatCurrency(totales.aporte_codemu)}`,
          tone: "danger",
        },
        {
          label: `Fondo común${pctFondo != null ? ` (${pctFondo}%)` : ""}`,
          value: `- ${formatCurrency(totales.fondo_comun)}`,
          tone: "danger",
        },
      ]}
      contextSlot={
        item.delegado_operacion_context ? (
          <section
            className="rounded-xl p-3 min-w-0"
            style={{
              border: "1px solid #bbf7d0",
              backgroundColor: "#f0fdf4",
              boxShadow: "inset 3px 0 0 #4ade80",
            }}
          >
            <span
              className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider mb-2"
              style={{ color: "#15803d" }}
            >
              <Banknote className="h-3 w-3" />
              Operatividad
            </span>
            <strong
              className="block text-[13px] font-bold text-green-800 truncate"
              title={item.delegado_operacion_context.municipalidad_nombre}
            >
              {item.delegado_operacion_context.municipalidad_nombre}
            </strong>
            <div className="flex flex-wrap gap-1 mt-1.5">
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
          </section>
        ) : (
          <section
            className="rounded-xl p-3 min-w-0"
            style={{
              border: "1px solid #eadedf",
              boxShadow: "inset 3px 0 0 #dca0a5",
            }}
          >
            <span
              className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider mb-2"
              style={{ color: "#a90c24" }}
            >
              <Banknote className="h-3 w-3" />
              Operatividad
            </span>
            <strong className="block text-[13px] font-medium text-neutral-500 truncate">
              Sin operatividad
            </strong>
            <span className="block text-[11px] mt-1.5 text-neutral-500">
              Flujo legacy
            </span>
          </section>
        )
      }
      actions={actions}
    >
      {/* Detalle de Liquidaciones — tabla compacta (dominio Delegado) */}
      <div className="p-3 rounded-lg border border-border/60 bg-muted/10">
        <div className="flex items-center gap-2 mb-2">
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
          <div className="overflow-x-auto max-h-96">
            <table className="w-full text-xs">
              <thead className="bg-muted/40">
                <tr>
                  <th className="border-b border-border px-2 py-1.5 text-center font-bold uppercase tracking-wide text-muted-foreground whitespace-nowrap">
                    Liq
                  </th>
                  <th className="border-b border-border px-2 py-1.5 text-left font-bold uppercase tracking-wide text-muted-foreground whitespace-nowrap">
                    N° Liq.
                  </th>
                  <th className="border-b border-border px-2 py-1.5 text-left font-bold uppercase tracking-wide text-muted-foreground whitespace-nowrap">
                    F. Rev.
                  </th>
                  <th className="border-b border-border px-2 py-1.5 text-left font-bold uppercase tracking-wide text-muted-foreground whitespace-nowrap">
                    Expediente
                  </th>
                  <th className="border-b border-border px-2 py-1.5 text-center font-bold uppercase tracking-wide text-muted-foreground whitespace-nowrap">
                    Nro Rev
                  </th>
                  <th className="border-b border-border px-2 py-1.5 text-left font-bold uppercase tracking-wide text-muted-foreground whitespace-nowrap">
                    Comprobante
                  </th>
                  <th className="border-b border-border px-2 py-1.5 text-right font-bold uppercase tracking-wide text-muted-foreground whitespace-nowrap">
                    Total
                  </th>
                  <th className="border-b border-border px-2 py-1.5 text-right font-bold uppercase tracking-wide text-muted-foreground whitespace-nowrap">
                    Sub Total
                  </th>
                  <th className="border-b border-border px-2 py-1.5 text-right font-bold uppercase tracking-wide text-muted-foreground whitespace-nowrap">
                    Imp. Bruto
                  </th>
                  <th className="border-b border-border px-2 py-1.5 text-right font-bold uppercase tracking-wide text-muted-foreground whitespace-nowrap">
                    CIP{pctRenta != null ? ` (${pctRenta}%)` : ""}
                  </th>
                  <th className="border-b border-border px-2 py-1.5 text-right font-bold uppercase tracking-wide text-muted-foreground whitespace-nowrap">
                    Aporte CODEMU
                    {pctAporte != null ? ` (${pctAporte}%)` : ""}
                  </th>
                  <th className="border-b border-border px-2 py-1.5 text-right font-bold uppercase tracking-wide text-muted-foreground whitespace-nowrap">
                    Fondo común
                    {pctFondo != null ? ` (${pctFondo}%)` : ""}
                  </th>
                  <th className="border-b border-border px-2 py-1.5 text-right font-bold uppercase tracking-wide text-muted-foreground whitespace-nowrap">
                    Neto Honorario
                  </th>
                  <th className="border-b border-border px-2 py-1.5 text-center font-bold uppercase tracking-wide text-muted-foreground whitespace-nowrap">
                    Nro RH
                  </th>
                </tr>
              </thead>
              <tbody>
                {detalles.map((detalle, index) => {
                  const comp = detalle.comprobante_activo;
                  const compLabel = comp
                    ? `${comp.tipo_comprobante ?? ""} ${
                        comp.serie ?? ""
                      }${comp.numero ?? ""}`.trim()
                    : null;
                  const filaKey = detalle.detalle_id ?? `fila-${index}`;
                  return (
                    <tr key={filaKey} className="hover:bg-muted/30">
                      <td className="border-b border-border/50 px-2 py-1 text-center">
                        {index + 1}
                      </td>
                      <td className="border-b border-border/50 px-2 py-1 font-mono whitespace-nowrap">
                        {detalle.liquidacion_especifica_numero ?? "—"}
                      </td>
                      <td className="border-b border-border/50 px-2 py-1 whitespace-nowrap">
                        {detalle.fecha_revision
                          ? formatDate(detalle.fecha_revision)
                          : "—"}
                      </td>
                      <td className="border-b border-border/50 px-2 py-1 font-mono font-medium">
                        {detalle.expediente || "—"}
                      </td>
                      <td className="border-b border-border/50 px-2 py-1 text-center">
                        {detalle.numero_revision ?? "—"}
                      </td>
                      <td className="border-b border-border/50 px-2 py-1 text-[10px] text-muted-foreground">
                        {compLabel ?? "—"}
                      </td>
                      <td className="border-b border-border/50 px-2 py-1 text-right whitespace-nowrap">
                        {detalle.total_liquidacion != null
                          ? formatCurrency(detalle.total_liquidacion)
                          : "—"}
                      </td>
                      <td className="border-b border-border/50 px-2 py-1 text-right whitespace-nowrap">
                        {detalle.sub_total_liquidacion != null
                          ? formatCurrency(detalle.sub_total_liquidacion)
                          : "—"}
                      </td>
                      <td className="border-b border-border/50 px-2 py-1 text-right whitespace-nowrap">
                        {detalle.imp_bruto != null
                          ? formatCurrency(detalle.imp_bruto)
                          : "—"}
                      </td>
                      <td className="border-b border-border/50 px-2 py-1 text-right text-destructive whitespace-nowrap">
                        {detalle.renta_cip != null
                          ? `- ${formatCurrency(detalle.renta_cip)}`
                          : "—"}
                      </td>
                      <td className="border-b border-border/50 px-2 py-1 text-right text-destructive whitespace-nowrap">
                        {detalle.aporte_codemu != null
                          ? `- ${formatCurrency(detalle.aporte_codemu)}`
                          : "—"}
                      </td>
                      <td className="border-b border-border/50 px-2 py-1 text-right text-destructive whitespace-nowrap">
                        {detalle.fondo_comun != null
                          ? `- ${formatCurrency(detalle.fondo_comun)}`
                          : "—"}
                      </td>
                      <td className="border-b border-border/50 px-2 py-1 text-right font-semibold whitespace-nowrap">
                        {detalle.neto_honorario != null
                          ? formatCurrency(detalle.neto_honorario)
                          : "—"}
                      </td>
                      <td className="border-b border-border/50 px-2 py-1 text-center">
                        {detalle.numero_rh ?? "—"}
                      </td>
                    </tr>
                  );
                })}
                {/* Fila de Totales */}
                <tr className="bg-muted/50 font-semibold">
                  <td
                    colSpan={6}
                    className="border-b border-border px-2 py-1.5 text-center uppercase tracking-wide"
                  >
                    Totales
                  </td>
                  <td className="border-b border-border px-2 py-1.5 text-right whitespace-nowrap">
                    {formatCurrency(
                      detalles.reduce(
                        (sum, d) => sum + (d.total_liquidacion ?? 0),
                        0,
                      ),
                    )}
                  </td>
                  <td className="border-b border-border px-2 py-1.5 text-right whitespace-nowrap">
                    {formatCurrency(
                      detalles.reduce(
                        (sum, d) => sum + (d.sub_total_liquidacion ?? 0),
                        0,
                      ),
                    )}
                  </td>
                  <td className="border-b border-border px-2 py-1.5 text-right whitespace-nowrap">
                    {formatCurrency(
                      detalles.reduce((sum, d) => sum + (d.imp_bruto ?? 0), 0),
                    )}
                  </td>
                  <td className="border-b border-border px-2 py-1.5 text-right text-destructive whitespace-nowrap">
                    - {formatCurrency(totales.renta_cip)}
                  </td>
                  <td className="border-b border-border px-2 py-1.5 text-right text-destructive whitespace-nowrap">
                    - {formatCurrency(totales.aporte_codemu)}
                  </td>
                  <td className="border-b border-border px-2 py-1.5 text-right text-destructive whitespace-nowrap">
                    - {formatCurrency(totales.fondo_comun)}
                  </td>
                  <td className="border-b border-border px-2 py-1.5 text-right font-black text-primary whitespace-nowrap">
                    {formatCurrency(totales.neto_honorario)}
                  </td>
                  <td className="border-b border-border px-2 py-1" />
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

      {/* Tasas aplicadas */}
      {item.variables_calculo && (
        <div className="p-3 rounded-lg border border-border/60 bg-muted/10 mt-4">
          <div className="flex items-center gap-2 mb-3">
            <Banknote className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
              Variables de cálculo
            </span>
          </div>
          <RhDelegadoVariablesCalculo
            tasa_renta_cip={item.variables_calculo.tasa_renta_cip}
            tasa_aporte_codemu={item.variables_calculo.tasa_aporte_codemu}
            tasa_fondo_comun={item.variables_calculo.tasa_fondo_comun}
            compact
          />
        </div>
      )}
    </RhMensualCardShell>
  );
}
