/**
 * printReactPdf — Impresión de un componente React como documento oficial.
 *
 * A diferencia de `printHtmlElement` (que clona un nodo ya construido), este
 * helper MONTA el componente React dentro del iframe aislado. Así el documento
 * impreso es EXACTAMENTE el mismo componente React que se ve en pantalla.
 *
 * Los documentos oficiales usan estilos INLINE (no clases de Tailwind) porque
 * el CSS de la app no está disponible dentro del iframe aislado; por eso no
 * hace falta copiarlo.
 *
 * Al terminar se invoca `window.print()` del iframe: el navegador abre su
 * panel de impresión con el documento ya maquetado.
 */

import type { ReactNode } from "react";
import { flushSync } from "react-dom";
import { createRoot } from "react-dom/client";
import { createPdfFrame, waitForImages } from "./pdfShell";

export interface PrintReactPdfOptions {
  /** CSS de impresión (por ejemplo `@page { size: A4 portrait }`). */
  pageCss?: string;
  /** Ancho del iframe: debe ser el del documento para maquetar igual. */
  width?: string;
}

/**
 * Monta `node` en un iframe aislado e invoca la impresión del navegador.
 */
export async function printReactPdf(
  node: ReactNode,
  title = "Documento",
  options: PrintReactPdfOptions = {},
) {
  const { frame, frameWindow, frameDocument } = createPdfFrame({
    position: "fixed",
    width: options.width ?? "780px",
    height: "1123px",
  });
  frameDocument.title = title;

  // El CSS de impresión es exclusivo de este documento: se inyecta aquí para
  // no tocar el helper compartido (que sirve a los PDF de Liquidaciones).
  if (options.pageCss) {
    const style = frameDocument.createElement("style");
    style.textContent = options.pageCss;
    frameDocument.head.appendChild(style);
  }

  const container = frameDocument.createElement("div");
  frameDocument.body.appendChild(container);

  const root = createRoot(container);
  try {
    // `flushSync` fuerza el commit síncrono: sin esto el panel de impresión
    // puede abrirse antes de que React haya pintado el documento.
    flushSync(() => root.render(node));

    await waitForImages(container);
    frameWindow.focus();
    frameWindow.print();

    setTimeout(() => frame.remove(), 1000);
  } catch (err) {
    frame.remove();
    throw err;
  }
}
