/**
 * printDocument — Impresión genérica de un elemento HTML como documento oficial.
 * Usa un iframe oculto + window.print() para aislar el CSS de la app.
 */
import { applyStyles, createPdfFrame, waitForImages } from "./pdfShell";

/**
 * Imprime el elemento dado. El elemento se clona dentro de un iframe aislado
 * (position fixed, 0x0) para que la impresión sea limpia.
 */
export async function printHtmlElement(
  element: HTMLElement,
  title = "Documento",
) {
  const { frame, frameWindow, frameDocument } = createPdfFrame({
    position: "fixed",
    width: "0",
    height: "0",
  });
  frameDocument.title = title;

  try {
    // Clonar el elemento al documento del iframe
    const cloned = element.cloneNode(true) as HTMLElement;
    applyStyles(cloned, {
      position: "static",
      left: "auto",
      top: "auto",
      width: "980px",
      margin: "0 auto",
    });
    frameDocument.body.appendChild(cloned);

    await waitForImages(cloned);
    frameWindow.focus();
    frameWindow.print();

    setTimeout(() => frame.remove(), 1000);
  } catch (err) {
    frame.remove();
    throw err;
  }
}
