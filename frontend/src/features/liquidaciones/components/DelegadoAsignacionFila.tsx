"use client";

import { Receipt } from "lucide-react";
import type { ReactNode } from "react";
import {
  DICTAMEN_REVISION_VALUES,
  type DictamenRevision,
  type LiquidacionDelegadoDetalle,
} from "../schemas/liquidacion-delegado-detalle.schema";
import { formatCurrency } from "./liquidacion-ui";

/**
 * DelegadoAsignacionFila — UNA fila de la TABLA de asignaciones de delegado.
 *
 * La fila es de SOLO LECTURA. No hay ningún `<input>`, `<select>`, campo de
 * fecha, ni acción de guardado: la metadata de la asignación, los importes
 * del detalle de honorario y la cabecera del RH mensual enlazado se muestran
 * como TEXTO. La edición de la asignación no se ofrece desde aquí.
 *
 * Granularidad (DD7): la fila es de ASIGNACIÓN; la remoción es de alcance
 * DELEGADO (la guarda del backend agrupa TODAS las filas de
 * `(liquidacion, delegado)`). Por eso el botón "Quitar delegado" NO vive en
 * una fila de asignación: vive en una columna de ACCIONES combinada (`rowSpan`)
 * con todas las filas de ese delegado. Un botón por fila mentiría sobre el
 * comportamiento real del backend.
 *
 * D4: `numero_rh` (asignación) y `recibo_mensual.numero` (cabecera del RH
 * mensual) son campos de entidades DISTINTAS y nunca se mezclan: cada uno
 * tiene su propia etiqueta.
 */

/** Etiquetas legibles de los valores de `dictamen_revision`. */
const DICTAMEN_LABELS: Record<DictamenRevision, string> = {
  CONFORME: "Conforme",
  NO_CONFORME: "No conforme",
  PENDIENTE: "Pendiente",
  AP_OB: "AP.OB.",
};

/**
 * Etiqueta legible del dictamen.
 *
 * Si el backend devuelve un valor conocido del enum, se usa su etiqueta;
 * si no, se muestra el valor tal cual (nunca se inventa una traducción).
 */
function etiquetaDictamen(valor: string | null | undefined): string {
  if (!valor) return "—";
  const conocido = DICTAMEN_REVISION_VALUES.find((v) => v === valor);
  return conocido ? DICTAMEN_LABELS[conocido] : valor;
}

/** Totales agregados del detalle de honorario de la asignación. */
type ResumenDetalleRh = {
  detalles: number;
  impBruto: number;
  rentaCip: number;
  aporteCodemu: number;
  fondoComun: number;
  netoHonorario: number;
};

/**
 * Resume el detalle RH de la asignación.
 *
 * Una asignación puede tener VARIOS `DetalleHonorarioDelegado`: las cifras
 * mostradas son la SUMA de todos ellos (el resumen de la fila).
 */
function resumirDetalleRh(
  asignacion: LiquidacionDelegadoDetalle,
): ResumenDetalleRh {
  return asignacion.detalle_rh.reduce<ResumenDetalleRh>(
    (acumulado, detalle) => ({
      detalles: acumulado.detalles + 1,
      impBruto: acumulado.impBruto + (detalle.imp_bruto ?? 0),
      rentaCip: acumulado.rentaCip + (detalle.renta_cip ?? 0),
      aporteCodemu: acumulado.aporteCodemu + (detalle.aporte_codemu ?? 0),
      fondoComun: acumulado.fondoComun + (detalle.fondo_comun ?? 0),
      netoHonorario: acumulado.netoHonorario + (detalle.neto_honorario ?? 0),
    }),
    {
      detalles: 0,
      impBruto: 0,
      rentaCip: 0,
      aporteCodemu: 0,
      fondoComun: 0,
      netoHonorario: 0,
    },
  );
}

/** Datos del delegado: identifican el grupo de filas (celda combinada). */
type DelegadoResumen = {
  nombre: string;
  cip: string | null;
  /** Nº de asignaciones del delegado (dato de grupo, no de fila). */
  totalAsignaciones: number;
};

interface DelegadoAsignacionFilaProps {
  /** La asignación tal como la devuelve el endpoint anidado de detalle. */
  asignacion: LiquidacionDelegadoDetalle;
  /** Datos del delegado: la celda se combina con todas sus filas. */
  delegado: DelegadoResumen;
  /**
   * `true` sólo en la PRIMERA fila del grupo: dibuja la celda del delegado y
   * la celda de acciones, ambas combinadas con `rowSpan`.
   */
  esPrimeraFilaDelGrupo: boolean;
  /**
   * Acción de remoción del DELEGADO (botón + motivo inline del rechazo).
   *
   * Se dibuja en su columna propia: su alcance es el delegado completo, nunca
   * una asignación suelta.
   */
  accion?: ReactNode;
}

export function DelegadoAsignacionFila({
  asignacion,
  delegado,
  esPrimeraFilaDelGrupo,
  accion,
}: DelegadoAsignacionFilaProps) {
  const resumen = resumirDetalleRh(asignacion);

  /** RH mensual enlazado (la asignación puede tener varios detalles). */
  const reciboMensual =
    asignacion.detalle_rh.find((detalle) => detalle.recibo_mensual != null)
      ?.recibo_mensual ?? null;

  return (
    <tr className="border-b border-border/40 align-top">
      {/* ── Delegado (celda combinada: cubre TODAS sus asignaciones) ── */}
      {esPrimeraFilaDelGrupo && (
        <td
          rowSpan={delegado.totalAsignaciones}
          className="w-60 border-r border-border/40 pr-3 align-top"
        >
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/10">
                <Receipt className="h-4 w-4 text-primary" />
              </span>
              <div className="flex min-w-0 flex-col">
                <span className="truncate text-xs font-semibold text-foreground">
                  {delegado.nombre}
                </span>
                {delegado.cip && (
                  <span className="mt-0.5 inline-flex w-fit items-center rounded-full border border-primary/20 bg-primary/10 px-2 py-0.5 text-[10px] font-bold whitespace-nowrap text-primary">
                    CIP {delegado.cip}
                  </span>
                )}
              </div>
            </div>
            <span className="text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
              {delegado.totalAsignaciones} asignación
              {delegado.totalAsignaciones === 1 ? "" : "es"}
            </span>
          </div>
        </td>
      )}

      <td className="px-3 py-3 text-xs font-semibold whitespace-nowrap">
        {asignacion.especialidad_revision.nombre}
      </td>
      <td className="px-3 py-3 text-xs whitespace-nowrap">{asignacion.tipo ?? "—"}</td>
      <td className="px-3 py-3 text-xs whitespace-nowrap">{asignacion.periodo ?? "—"}</td>
      <td className="px-3 py-3 text-xs whitespace-nowrap">{asignacion.mes ?? "—"}</td>
      <td className="px-3 py-3 text-xs whitespace-nowrap">{etiquetaDictamen(asignacion.dictamen_revision)}</td>
      <td className="px-3 py-3 text-xs whitespace-nowrap">{asignacion.numero_rh ?? "—"}</td>
      <td className="px-3 py-3 text-xs whitespace-nowrap">{asignacion.fecha_presentacion ?? "—"}</td>
      <td className="px-3 py-3 text-xs whitespace-nowrap">{asignacion.fecha_revision ?? "—"}</td>
      <td className="px-3 py-3 text-xs font-semibold whitespace-nowrap">{resumen.detalles ? formatCurrency(resumen.impBruto) : "—"}</td>
      <td className="px-3 py-3 text-xs font-semibold whitespace-nowrap">{resumen.detalles ? formatCurrency(resumen.netoHonorario) : "—"}</td>
      <td className="px-3 py-3 text-xs whitespace-nowrap">{resumen.detalles ? formatCurrency(resumen.rentaCip) : "—"}</td>
      <td className="px-3 py-3 text-xs whitespace-nowrap">{resumen.detalles ? formatCurrency(resumen.aporteCodemu) : "—"}</td>
      <td className="px-3 py-3 text-xs whitespace-nowrap">{resumen.detalles ? formatCurrency(resumen.fondoComun) : "—"}</td>
      <td className="px-3 py-3 text-xs whitespace-nowrap">
        {reciboMensual ? `RH mensual #${reciboMensual.numero ?? "—"}` : "Registro legacy"}
      </td>

      {/* ── Acción delegada: una sola celda por grupo ── */}
      {esPrimeraFilaDelGrupo && (
        <td
          rowSpan={delegado.totalAsignaciones}
          className="w-36 px-3 py-3 text-right align-top"
        >
          {accion}
        </td>
      )}
    </tr>
  );
}
