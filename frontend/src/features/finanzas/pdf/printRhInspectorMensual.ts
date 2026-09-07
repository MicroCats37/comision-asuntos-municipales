/**
 * printRhInspectorMensual — Impresión directa de un Recibo de Honorarios Mensual de Inspector.
 * Construye el HTML del documento (usando pdfShell infra) y abre la interfaz nativa de impresión.
 */
import { createPdfFrame } from "@/components-app/pdf/pdfShell";
import { printHtmlElement } from "@/components-app/pdf/printDocument";
import { buildRhInspectorPdfElement } from "./buildRhInspectorPdfElement";
import type { ReciboHonorarioInspectorMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";

/**
 * Imprime un Recibo de Honorarios Mensual de Inspector (interfaz nativa del navegador).
 * @param item datos del RH (del backend)
 */
export async function printRhInspectorMensual(item: ReciboHonorarioInspectorMensual) {
  const { frame, frameDocument } = createPdfFrame();
  try {
    const pdfElement = buildRhInspectorPdfElement(item, frameDocument);
    const docId = item.id;
    await printHtmlElement(pdfElement, docId);
  } finally {
    frame.remove();
  }
}
