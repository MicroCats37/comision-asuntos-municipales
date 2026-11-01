/**
 * printRhInspectorMensual — Impresión directa de un Recibo de Honorarios Mensual
 * de Inspector.
 *
 * Monta el componente React `RhInspectorMensualPdf` en un iframe aislado: lo
 * que se imprime es EXACTAMENTE lo que se ve en la vista previa de la UI.
 */
import { printReactPdf } from "@/components-app/pdf/printReactPdf";
import type { ReciboHonorarioInspectorMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";
import { RhInspectorMensualPdf } from "./RhInspectorMensualPdf";
import { RH_PDF_PAGE_CSS } from "./rhPdfPage";

/**
 * Imprime un Recibo de Honorario Mensual de Inspector (interfaz nativa del navegador).
 *
 * Se imprime en A4 apaisada: la tabla tiene 11 columnas y en vertical se
 * cortarían.
 *
 * @param item datos del RH (del backend)
 */
export async function printRhInspectorMensual(
  item: ReciboHonorarioInspectorMensual,
) {
  await printReactPdf(<RhInspectorMensualPdf item={item} />, item.id, {
    pageCss: RH_PDF_PAGE_CSS,
    width: "1040px",
  });
}
