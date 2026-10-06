/**
 * printRhDelegadoMensual — Impresión directa de una liquidacion RH Delegado Mensual.
 * Construye el HTML del documento (usando pdfShell infra) y abre la interfaz nativa de impresión.
 */
import { createPdfFrame } from "@/components-app/pdf/pdfShell";
import { printHtmlElement } from "@/components-app/pdf/printDocument";
import { buildRhDelegadoPdfElement } from "./buildRhDelegadoPdfElement";
import type { ReciboHonorarioDelegadoMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";

/**
 * Imprime una liquidacion RH Delegado Mensual directa (interfaz nativa del navegador).
 * @param item datos del RH (del backend)
 */
export async function printRhDelegadoMensual(
  item: ReciboHonorarioDelegadoMensual,
) {
  const { frame, frameDocument } = createPdfFrame();
  try {
    const pdfElement = buildRhDelegadoPdfElement(item, frameDocument);
    const docId = item.id;
    await printHtmlElement(pdfElement, docId);
  } finally {
    frame.remove();
  }
}
