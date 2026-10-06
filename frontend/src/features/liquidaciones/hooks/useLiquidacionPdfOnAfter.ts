/**
 * useLiquidacionPdfOnAfter
 *
 * Hook compartido para los 6 FormModals de liquidaciones.
 * Devuelve un `onAfterSubmit` que abre el PDF preview tras cualquier flujo de
 * creación (`create`, `nueva-revision`, `relacionada`), siguiendo la misma
 * arquitectura que el flujo `create` original. Edit no se considera: no produce
 * un wrapper nuevo y la mutación devuelve void.
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
import type { PdfLiquidacionItem } from "../pdf/buildLiquidacionPdfElement";
import {
  type PdfTipoSlug,
  printLiquidacionPreview,
} from "../pdf/LiquidacionPdfPreview";

const CREATION_MODES: ReadonlySet<LiquidacionFormMode> = new Set([
  "create",
  "nueva-revision",
  "relacionada",
]);

export function useLiquidacionPdfOnAfter(tipoPdf: PdfTipoSlug) {
  return useCallback(
    (submitMode: LiquidacionFormMode, result: unknown) => {
      if (!CREATION_MODES.has(submitMode)) return;

      const envelope = result as
        | { data?: PdfLiquidacionItem }
        | null
        | undefined;
      const created =
        envelope?.data ?? (result as PdfLiquidacionItem | undefined);
      if (!created) {
        notify.success("Liquidación creada correctamente");
        return;
      }

      void printLiquidacionPreview(created, tipoPdf).then(
        () => notify.success("Liquidación creada correctamente"),
        (error) => {
          console.error(
            "No se pudo abrir la impresión de la liquidación",
            error,
          );
          notify.success("Liquidación creada correctamente");
          notify.error("No se pudo abrir la impresión");
        },
      );
    },
    [tipoPdf],
  );
}
