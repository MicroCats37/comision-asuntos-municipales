"use client";

/**
 * ReciboHonorarioInspectorMensualCard — Card para mostrar un Recibo de Honorario
 * Mensual del inspector.
 *
 * La ESTRUCTURA, el header, el resumen y las acciones viven en el shell común
 * `RhMensualCardShell` (compartido con la card de Delegado). Lo específico del
 * dominio —la tabla de Inspecciones de Obra, el resumen de inspecciones y las
 * variables de cálculo— se mantiene aquí.
 */
import {
  Banknote,
  FileDown,
  FilePenLine,
  FileText,
  HardHat,
  Trash2,
} from "lucide-react";
import {
  type RhCardAction,
  RhMensualCardShell,
} from "@/features/finanzas/components/cards/RhMensualCardShell";
import { RhInspectorVariablesCalculo } from "@/features/finanzas/components/RhInspectorVariablesCalculo";
import { printRhInspectorMensual } from "@/features/finanzas/pdf/printRhInspectorMensual";
import type { ReciboHonorarioInspectorMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";
import { formatCurrency } from "@/features/liquidaciones/components/liquidacion-ui";

interface ReciboHonorarioInspectorMensualCardProps {
  item: ReciboHonorarioInspectorMensual;
  onDelete?: (id: string) => void;
  /** Abre el modal de RH mensual en modo edición con este recibo. */
  onEdit?: (item: ReciboHonorarioInspectorMensual) => void;
}

export function ReciboHonorarioInspectorMensualCard({
  item,
  onDelete,
  onEdit,
}: ReciboHonorarioInspectorMensualCardProps) {
  const insp = item.inspector;
  const totales = item.totales;
  const detalles = item.detalles || [];
  const ioCount = detalles.length;

  const handlePrint = () => {
    printRhInspectorMensual(item);
  };

  const handleDelete = () => {
    onDelete?.(item.id);
  };

  const handleEdit = () => {
    onEdit?.(item);
  };

  /**
   * Acciones del recibo — mismo orden, dimensiones, iconos y política de
   * texto que la card de Delegado (shell común).
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
      kindIcon={HardHat}
      kindLabel="Inspector"
      rhNumero={item.numero}
      fechaRegistro={item.fecha_registro}
      periodo={{ periodo: item.periodo, mes: item.mes }}
      personaNombre={insp?.nombre_completo ?? null}
      personaDocumento={insp?.cip ? `CIP: ${insp.cip}` : null}
      totalLabel="Neto a pagar"
      total={totales.honorarios}
      summaryItems={[
        { label: "Subtotal", value: formatCurrency(totales.sub_total) },
        {
          label: "Descuento",
          value: `- ${formatCurrency(totales.descuento)}`,
          tone: "danger",
        },
      ]}
      actions={actions}
    >
      {/* IO incluidas — compact table (dominio Inspector) */}
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
                    Rev.
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
                  <th className="text-right text-[10px] font-semibold text-muted-foreground uppercase tracking-wider pb-1.5 pl-3 whitespace-nowrap">
                    Honorarios
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
                      <td className="py-1.5 pr-3 text-muted-foreground text-center whitespace-nowrap">
                        {detalle.numero_revision ?? "—"}
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
                      <td className="py-1.5 pl-3 text-right font-medium text-muted-foreground whitespace-nowrap">
                        {detalle.honorarios != null
                          ? formatCurrency(Number(detalle.honorarios))
                          : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              {/* Totals row */}
              <tfoot>
                <tr className="border-t border-border/50 bg-muted/20">
                  <td
                    colSpan={8}
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
                  <td className="py-1.5 pl-3 text-right font-bold text-primary whitespace-nowrap">
                    {totales.honorarios != null
                      ? formatCurrency(totales.honorarios)
                      : "—"}
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
      <div className="p-3 rounded-lg border border-border/60 bg-muted/10 mt-4">
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
            <p className="text-sm font-semibold">{totales.saldo_restante}</p>
          </div>
        </div>
      </div>

      {/* Variables de cálculo aplicadas */}
      <div className="p-3 rounded-lg border border-border/60 bg-muted/10 mt-4">
        <div className="flex items-center gap-2 mb-3">
          <Banknote className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
            Variables de cálculo
          </span>
        </div>
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
    </RhMensualCardShell>
  );
}
