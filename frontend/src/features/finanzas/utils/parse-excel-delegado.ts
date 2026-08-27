/**
 * Parsea un Excel con columna Expediente y genera los items
 * para auto-check en RhDelegadoMensualModal.
 *
 * Formato esperado del archivo:
 *   - Columna "Expediente": número/texto del expediente a buscar
 *
 * Returns array of expediente strings found in the file.
 */
import * as XLSX from "xlsx";

export async function parseExcelFileDelegado(
  file: File,
): Promise<string[]> {
  const buffer = await file.arrayBuffer();
  const workbook = XLSX.read(buffer, { type: "array" });
  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet);

  const expedientes = rows
    .map((row) => String(row.Expediente ?? "").trim())
    .filter((exp) => exp !== "");

  return expedientes;
}
