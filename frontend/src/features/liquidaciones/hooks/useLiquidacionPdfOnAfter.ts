/**
 * useLiquidacionPdfOnAfter
 *
 * Hook compartido para los 6 FormModals de liquidaciones.
 * Devuelve un `onAfterSubmit` que abre el PDF preview tras cualquier flujo que
 * deja una liquidación imprimible (`create`, `nueva-revision`, `relacionada`,
 * `edit`), siguiendo la misma arquitectura que el flujo `create` original.
 *
 * Reutiliza el patrón toast + printLiquidacionPreview + fallback con manejo de
 * error. La única parte tipo-específica es `tipoPdf` (slug del tipo, p.ej.
 * "inspeccion-obra", "edificaciones"), que se pasa al `printLiquidacionPreview`.
 *
 * Reemplaza los ~15 líneas de `onAfterSubmit` duplicadas en cada FormModal.
 */
import { useCallback } from "react";
import { notify } from "@/errors";
import type { LiquidacionFormMode } from "../components/forms/LiquidacionFormHeader";
import { printLiquidacionPreview } from "../pdf/LiquidacionPdfPreview";
import type { PdfLiquidacionItem, PdfTipoSlug } from "../pdf/pdfTypes";

/** Modos que dejan una liquidación lista para imprimir. */
const PRINTABLE_MODES: ReadonlySet<LiquidacionFormMode> = new Set([
  "create",
  "nueva-revision",
  "relacionada",
  "edit",
]);

export function useLiquidacionPdfOnAfter(tipoPdf: PdfTipoSlug) {
  return useCallback(
    (submitMode: LiquidacionFormMode, result: unknown) => {
      if (!PRINTABLE_MODES.has(submitMode)) return;

      // Todos los hooks de liquidación (crear / editar) responden el envelope
      // `{ success, data, message }`. El payload imprimible vive en `data`.
      const envelope = result as
        | { data?: PdfLiquidacionItem }
        | null
        | undefined;
      const created =
        envelope?.data ?? (result as PdfLiquidacionItem | undefined);
      if (!created) {
        notify.success("Liquidación guardada correctamente");
        return;
      }

      void printLiquidacionPreview(created, tipoPdf).then(
        () => notify.success("Liquidación guardada correctamente"),
        (error) => {
          console.error(
            "No se pudo abrir la impresión de la liquidación",
            error,
          );
          notify.success("Liquidación guardada correctamente");
          notify.error("No se pudo abrir la impresión");
        },
      );
    },
    [tipoPdf],
  );
}
