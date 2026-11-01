/**
 * printRhDelegadoMensual — Impresión directa de una liquidacion RH Delegado Mensual.
 *
 * Monta el componente React `RhDelegadoMensualPdf` en un iframe aislado: lo
 * que se imprime es EXACTAMENTE lo que se ve en la vista previa de la UI.
 */
import { printReactPdf } from "@/components-app/pdf/printReactPdf";
import type { ReciboHonorarioDelegadoMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";
import { RhDelegadoMensualPdf } from "./RhDelegadoMensualPdf";
import { RH_PDF_PAGE_CSS } from "./rhPdfPage";

/**
 * Imprime una liquidacion RH Delegado Mensual directa (interfaz nativa del navegador).
 *
 * Se imprime en A4 apaisada: la tabla tiene 14 columnas y en vertical se
 * cortarían.
 *
 * @param item datos del RH (del backend)
 */
export async function printRhDelegadoMensual(
  item: ReciboHonorarioDelegadoMensual,
) {
  await printReactPdf(<RhDelegadoMensualPdf item={item} />, item.id, {
    pageCss: RH_PDF_PAGE_CSS,
    width: "1040px",
  });
}
