/**
 * Exportación a Excel del detalle RH (Delegados e Inspectores).
 *
 * El libro se arma en el frontend: la API devuelve el conjunto COMPLETO
 * filtrado (sin_paginacion=true) y este helper usa las mismas columnas que
 * la tabla más una fila de TOTALES.
 *
 * Las columnas se derivan de los formatters compartidos en
 * `components/tables/RHDetalleTable.types.ts` para que el Excel y la tabla
 * nunca diverjan.
 */
import * as XLSX from "xlsx";
import {
  type DetalleDelegadoRow,
  type DetalleInspectorRow,
  formatDelegadoRow,
  formatInspectorRow,
} from "@/features/finanzas/components/tables/RHDetalleTable.types";

/** Normaliza un valor para usarlo como parte de un nombre de archivo. */
export function safeFilePart(value: string): string {
  return value.replace(/[^a-zA-Z0-9-]/g, "-");
}

export interface RhDetalleExcelPeriodo {
  periodo: number;
  mes: number;
}

type ExcelRow = Record<string, string | number>;

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

function periodoFila(periodo: string | null, mes: number | null): string {
  if (!periodo || mes == null) return "";
  return `${periodo}/${String(mes).padStart(2, "0")}`;
}

/**
 * Exporta el detalle de Delegados con una fila de TOTALES al final.
 */
export function exportRhDetalleDelegadosExcel(
  rows: DetalleDelegadoRow[],
  periodo: RhDetalleExcelPeriodo,
): void {
  const data = rows.map(formatDelegadoRow);

  const sheet: ExcelRow[] = data.map((row, index) => ({
    Item: index + 1,
    "N° RH": row.numeroRh ?? "",
    Expediente: row.expediente ?? "",
    "N° Liquidación": row.numero ?? "",
    Tipo: row.tipoNombre ?? row.tipoCodigo ?? "",
    Delegado: row.delegadoNombre ?? "",
    CIP: row.delegadoCip ?? "",
    Periodo: periodoFila(row.periodo, row.mes),
    Dictamen: row.dictamenRevision ?? "",
    "F. Presentación": row.fechaPresentacion ?? "",
    "F. Revisión": row.fechaRevision ?? "",
    "Imp. Bruto": row.impBruto ?? 0,
    "Renta CIP": row.rentaCip ?? 0,
    "Aporte CODEMU": row.aporteCodem ?? 0,
    "Fondo Común": row.fondoComun ?? 0,
    "Neto Honorario": row.neto ?? 0,
  }));

  sheet.push({
    Item: "",
    "N° RH": "",
    Expediente: "",
    "N° Liquidación": "",
    Tipo: "",
    Delegado: "TOTALES",
    CIP: "",
    Periodo: periodoLabel(periodo.periodo, periodo.mes),
    Dictamen: "",
    "F. Presentación": "",
    "F. Revisión": "",
    "Imp. Bruto": data.reduce((sum, r) => sum + (r.impBruto ?? 0), 0),
    "Renta CIP": data.reduce((sum, r) => sum + (r.rentaCip ?? 0), 0),
    "Aporte CODEMU": data.reduce((sum, r) => sum + (r.aporteCodem ?? 0), 0),
    "Fondo Común": data.reduce((sum, r) => sum + (r.fondoComun ?? 0), 0),
    "Neto Honorario": data.reduce((sum, r) => sum + (r.neto ?? 0), 0),
  });

  descargarLibro(
    sheet,
    "Detalle RH Delegados",
    `rh-detalle-delegados-${periodoLabel(periodo.periodo, periodo.mes)}.xlsx`,
  );
}

/**
 * Exporta el detalle de Inspectores con una fila de TOTALES al final.
 */
export function exportRhDetalleInspectoresExcel(
  rows: DetalleInspectorRow[],
  periodo: RhDetalleExcelPeriodo,
): void {
  const data = rows.map(formatInspectorRow);

  const sheet: ExcelRow[] = data.map((row, index) => ({
    Item: index + 1,
    Expediente: row.expediente ?? "",
    "N° Liquidación": row.numero ?? "",
    Tipo: row.tipoCodigo ?? "",
    Inspector: row.inspectorNombre ?? "",
    CIP: row.inspectorCip ?? "",
    Periodo: periodoFila(
      row.periodo != null ? String(row.periodo) : null,
      row.mes,
    ),
    Dictamen: row.dictamenRevision ?? "",
    "F. Presentación": row.fechaPresentacion ?? "",
    "F. Revisión": row.fechaRevision ?? "",
    "Insp. Liquidadas": row.inspLiq ?? 0,
    "Costo Insp.": row.costoInsp ?? 0,
    "Monto Contribuido": row.montoContrib ?? 0,
    "Sub Total": row.subTotal ?? 0,
    Descuento: row.descuento ?? 0,
    Honorarios: row.honorarios ?? 0,
  }));

  sheet.push({
    Item: "",
    Expediente: "",
    "N° Liquidación": "",
    Tipo: "",
    Inspector: "TOTALES",
    CIP: "",
    Periodo: periodoLabel(periodo.periodo, periodo.mes),
    Dictamen: "",
    "F. Presentación": "",
    "F. Revisión": "",
    "Insp. Liquidadas": data.reduce((sum, r) => sum + (r.inspLiq ?? 0), 0),
    "Costo Insp.": data.reduce((sum, r) => sum + (r.costoInsp ?? 0), 0),
    "Monto Contribuido": data.reduce(
      (sum, r) => sum + (r.montoContrib ?? 0),
      0,
    ),
    "Sub Total": data.reduce((sum, r) => sum + (r.subTotal ?? 0), 0),
    Descuento: data.reduce((sum, r) => sum + (r.descuento ?? 0), 0),
    Honorarios: data.reduce((sum, r) => sum + (r.honorarios ?? 0), 0),
  });

  descargarLibro(
    sheet,
    "Detalle RH Inspectores",
    `rh-detalle-inspectores-${periodoLabel(periodo.periodo, periodo.mes)}.xlsx`,
  );
}
