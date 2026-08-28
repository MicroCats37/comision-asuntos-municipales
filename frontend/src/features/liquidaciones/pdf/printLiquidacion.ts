/**
 * printLiquidacion — Impresión directa de una liquidación.
 * Construye el HTML del PDF (base común + motor) y abre la interfaz nativa de impresión.
 * NO usa modal ni html2canvas — directo window.print() con el HTML listo.
 */
import { createPdfFrame } from "@/components-app/pdf/pdfShell";
import { printHtmlElement } from "@/components-app/pdf/printDocument";
import {
  buildLiquidacionPdfElement,
  type PdfLiquidacionItem,
} from "./buildLiquidacionPdfElement";

/**
 * Imprime una liquidación directo (interfaz nativa del navegador).
 * @param item datos de la liquidación (del backend)
 * @param tipo "edificacion" | "taludes" | ... (para título y motor)
 */
export async function printLiquidacion(item: PdfLiquidacionItem, tipo: string) {
  const { frame, frameDocument } = createPdfFrame();
  try {
    const pdfElement = buildLiquidacionPdfElement(item, tipo, frameDocument);
    const docId =
      item.liquidacion_general.expediente || item.liquidacion_general.id;
    await printHtmlElement(pdfElement, docId);
  } finally {
    frame.remove();
  }
}
