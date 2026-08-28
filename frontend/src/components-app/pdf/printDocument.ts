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
  const frame = document.createElement("iframe");
  applyStyles(frame, {
    position: "fixed",
    right: "0",
    bottom: "0",
    width: "0",
    height: "0",
    border: "0",
  });

  try {
    document.body.appendChild(frame);

    const frameWindow = frame.contentWindow;
    const frameDocument = frame.contentDocument;
    if (!frameWindow || !frameDocument) {
      throw new Error("No se pudo crear el documento aislado para impresión.");
    }

    frameDocument.open();
    frameDocument.write(
      `<!doctype html><html><head><meta charset="utf-8"><title>${title}</title></head><body style="margin:0;background:#FFFFFF;"></body></html>`,
    );
    frameDocument.close();

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
