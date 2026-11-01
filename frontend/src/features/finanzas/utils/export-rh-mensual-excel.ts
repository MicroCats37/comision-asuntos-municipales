/**
 * Exportación a Excel del listado de RH MENSUAL (Delegados e Inspectores).
 *
 * Una fila por LIQUIDACIÓN (detalle del RH), no por recibo: se aplana el
 * `detalles[]` que el listado ya devuelve anidado en cada RH. El Excel lleva
 * el contexto del recibo (N° RH, persona, periodo) + el detalle de la
 * liquidación (expediente, fechas, dictamen, importes) y cierra con una fila
 * de TOTALES.
 *
 * Se genera en el frontend: la API devuelve el conjunto COMPLETO filtrado
 * (sin_paginacion=true) y aquí se aplana.
 */
import * as XLSX from "xlsx";
import type {
  ReciboHonorarioDelegadoMensual,
  ReciboHonorarioInspectorMensual,
} from "@/features/finanzas/schemas/recibo-honorario.schema";
import { safeFilePart } from "./export-rh-detalle-excel";

type ExcelRow = Record<string, string | number>;

export interface RhMensualExcelPeriodo {
  periodo: number;
  mes: number;
}

function periodoLabel(periodo: number, mes: number): string {
  return `${periodo}-${String(mes).padStart(2, "0")}`;
}

function descargarLibro(
  rows: ExcelRow[],
  sheetName: string,
  fileName: string,
): void {
  const workbook = XLSX.utils.book_new();
  const worksheet = XLSX.utils.json_to_sheet(rows);
  XLSX.utils.book_append_sheet(workbook, worksheet, sheetName);
  XLSX.writeFile(workbook, fileName);
}

const suma = (filas: ExcelRow[], clave: string) =>
  filas.reduce((acc, fila) => acc + (Number(fila[clave]) || 0), 0);

/**
 * Aplana los RH de Delegado en una fila por liquidación.
 */
export function buildRhMensualDelegadosRows(
  rows: ReciboHonorarioDelegadoMensual[],
): ExcelRow[] {
  const salida: ExcelRow[] = [];
  let item = 0;

  for (const rh of rows) {
    const persona = rh.delegado?.nombre_completo ?? "";
    const cip = rh.delegado?.cip ?? "";

    for (const det of rh.detalles ?? []) {
      item += 1;
      salida.push({
        Item: item,
        "N° RH": rh.numero ?? "",
        Delegado: persona,
        CIP: cip,
        Periodo: rh.periodo ?? "",
        Mes: rh.mes ?? "",
        "Nro Liq.": det.liquidacion_especifica_numero ?? "",
        Expediente: det.expediente ?? "",
        "Nro revision": det.numero_revision ?? "",
        "Nro Comp.": det.comprobante_activo
          ? `${det.comprobante_activo.serie ?? ""}-${det.comprobante_activo.numero ?? ""}`
          : "",
        "Fecha revision": det.fecha_revision ?? "",
        Dictamen: det.dictamen_revision ?? "",
        "Fecha presentacion": det.fecha_presentacion ?? "",
        "Total liquidacion": det.total_liquidacion ?? 0,
        "Sub total liquidacion": det.sub_total_liquidacion ?? 0,
        "Importe bruto": det.imp_bruto ?? 0,
        "Renta CIP": det.renta_cip ?? 0,
        "Aporte CODEMU": det.aporte_codemu ?? 0,
        "Fondo común": det.fondo_comun ?? 0,
        "Neto honorario": det.neto_honorario ?? 0,
      });
    }
  }

  return salida;
}

/**
 * Aplana los RH de Inspector en una fila por IO (liquidación).
 */
export function buildRhMensualInspectoresRows(
  rows: ReciboHonorarioInspectorMensual[],
): ExcelRow[] {
  const salida: ExcelRow[] = [];
  let item = 0;

  for (const rh of rows) {
    const persona = rh.inspector?.nombre_completo ?? "";
    const cip = rh.inspector?.cip ?? "";

    for (const det of rh.detalles ?? []) {
      item += 1;
      salida.push({
        Item: item,
        "N° RH": rh.numero ?? "",
        Inspector: persona,
        CIP: cip,
        Periodo: rh.periodo ?? "",
        Mes: rh.mes ?? "",
        "Nro Liq.": det.liquidacion_especifica_numero ?? "",
        Expediente: det.expediente ?? "",
        Propietario: det.nombre_propietario ?? "",
        Distrito: det.distrito ?? "",
        "Nro revision": det.numero_revision ?? "",
        "Nro Comp.": det.comprobante_activo
          ? `${det.comprobante_activo.serie ?? ""}-${det.comprobante_activo.numero ?? ""}`
          : "",
        "Fecha revision": det.fecha_revision ?? "",
        Dictamen: det.dictamen_revision ?? "",
        "Fecha presentacion": det.fecha_presentacion ?? "",
        "Insp. programadas": det.inspecciones_programadas ?? 0,
        "Insp. liquidadas": det.inspecciones_liquidadas ?? 0,
        "Costo/Unidad": det.costo_por_inspeccion ?? 0,
        "Monto Contribuido": det.monto_contribuido ?? 0,
        "Saldo restante": det.saldo_restante ?? 0,
        "Sub Total": det.sub_total ?? 0,
        Descuento: det.descuento ?? 0,
        Honorarios: det.honorarios ?? 0,
      });
    }
  }

  return salida;
}

/**
 * Exporta el detalle de liquidaciones de los RH de Delegado.
 */
export function exportRhMensualDelegadosExcel(
  rows: ReciboHonorarioDelegadoMensual[],
  periodo: RhMensualExcelPeriodo,
): void {
  const detalle = buildRhMensualDelegadosRows(rows);

  const totales: ExcelRow = {
    Item: "",
    "N° RH": "",
    Delegado: "TOTALES",
    CIP: "",
    Periodo: periodoLabel(periodo.periodo, periodo.mes),
    Mes: periodo.mes,
    "Nro Liq.": "",
    Expediente: "",
    "Nro revision": "",
    "Nro Comp.": "",
    "Fecha revision": "",
    Dictamen: "",
    "Fecha presentacion": "",
  };
  for (const clave of [
    "Total liquidacion",
    "Sub total liquidacion",
    "Importe bruto",
    "Renta CIP",
    "Aporte CODEMU",
    "Fondo común",
    "Neto honorario",
  ]) {
    totales[clave] = suma(detalle, clave);
  }

  descargarLibro(
    [...detalle, totales],
    "RH Mensual Delegados",
    `rh-mensual-delegados-${periodoLabel(periodo.periodo, periodo.mes)}.xlsx`,
  );
}

/**
 * Exporta el detalle de liquidaciones de los RH de Inspectores.
 */
export function exportRhMensualInspectoresExcel(
  rows: ReciboHonorarioInspectorMensual[],
  periodo: RhMensualExcelPeriodo,
): void {
  const detalle = buildRhMensualInspectoresRows(rows);

  const totales: ExcelRow = {
    Item: "",
    "N° RH": "",
    Inspector: "TOTALES",
    CIP: "",
    Periodo: periodoLabel(periodo.periodo, periodo.mes),
    Mes: periodo.mes,
    "Nro Liq.": "",
    Expediente: "",
    Propietario: "",
    Distrito: "",
    "Nro revision": "",
    "Nro Comp.": "",
    "Fecha revision": "",
    Dictamen: "",
    "Fecha presentacion": "",
  };
  for (const clave of [
    "Insp. programadas",
    "Insp. liquidadas",
    "Costo/Unidad",
    "Monto Contribuido",
    "Saldo restante",
    "Sub Total",
    "Descuento",
    "Honorarios",
  ]) {
    totales[clave] = suma(detalle, clave);
  }

  descargarLibro(
    [...detalle, totales],
    "RH Mensual Inspectores",
    `rh-mensual-inspectores-${periodoLabel(periodo.periodo, periodo.mes)}.xlsx`,
  );
}

/** Reexporta el helper de sanitización para los nombres de archivo. */
export { safeFilePart };
