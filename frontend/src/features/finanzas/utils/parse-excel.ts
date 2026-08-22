/**
 * Parsea un Excel con columnas: CIP, Expediente, Cantidad_Visitas
 * y genera el payload de cotización del RH mensual del inspector.
 */
import * as XLSX from "xlsx";
import type { RHInspectorCotizarIn } from "../schemas/rh-inspector-mensual.schema";

export async function parseExcelFile(
  file: File,
): Promise<RHInspectorCotizarIn> {
  const buffer = await file.arrayBuffer();
  const workbook = XLSX.read(buffer, { type: "array" });
  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet);

  const items = rows
    .map((row) => ({
      exp_liqui: String(row.Expediente ?? "").trim(),
      cantidad_visitas: Number(row.Cantidad_Visitas ?? 0),
    }))
    .filter((it) => it.exp_liqui !== "");

  // CIP de la primera fila (campo opcional del archivo)
  const cip = rows.length > 0 ? String(rows[0].CIP ?? "").trim() : "";
  const periodo = ""; // se completa en el modal

  return { cip, periodo, items };
}
