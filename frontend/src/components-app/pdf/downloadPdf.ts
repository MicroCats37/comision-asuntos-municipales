/**
 * downloadPdf — Descarga genérica de un elemento HTML como PDF.
 * Librería: html2canvas (HTML → canvas) + jsPDF (canvas → PDF A4 horizontal).
 * Soporta multi-página cuando el contenido excede una hoja.
 */
import { createPdfFrame, waitForImages } from "./pdfShell";

export async function downloadHtmlAsPdf(
  element: HTMLElement,
  fileName: string,
) {
  const [html2canvasMod, jsPDFMod] = await Promise.all([
    import("html2canvas"),
    import("jspdf"),
  ]);
  const html2canvas = html2canvasMod.default;
  const jsPDF = jsPDFMod.default;

  // Construir en un frame aislado para evitar contaminación CSS
  const { frame, frameDocument } = createPdfFrame();
  try {
    const cloned = element.cloneNode(true) as HTMLElement;
    frameDocument.body.appendChild(cloned);

    await waitForImages(cloned);
    const canvas = await html2canvas(cloned, {
      scale: 2,
      useCORS: true,
      backgroundColor: "#FFFFFF",
      logging: false,
    });

    const imgData = canvas.toDataURL("image/jpeg", 0.95);
    const pdf = new jsPDF("l", "mm", "a4");
    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = (canvas.height * pdfWidth) / canvas.width;

    let heightLeft = pdfHeight;
    let position = 0;

    pdf.addImage(imgData, "JPEG", 0, position, pdfWidth, pdfHeight);
    heightLeft -= pdf.internal.pageSize.getHeight();

    while (heightLeft > 0) {
      position = -(
        pdf.internal.pageSize.getHeight() *
        (pdf.internal.pages.length - 1)
      );
      pdf.addPage();
      pdf.addImage(imgData, "JPEG", 0, position, pdfWidth, pdfHeight);
      heightLeft -= pdf.internal.pageSize.getHeight();
    }

    pdf.save(fileName);
  } finally {
    frame.remove();
  }
}
