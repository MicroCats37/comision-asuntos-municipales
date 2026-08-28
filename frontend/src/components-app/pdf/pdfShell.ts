/**
 * pdfShell — Helpers base para generación de PDFs de liquidaciones.
 * Librería: html2canvas + jsPDF (descarga), iframe + window.print (impresión).
 *
 * TODO lo que es común a cualquier liquidación vive aquí:
 * - applyStyles, waitForImages, appendReceiptRow
 * - formatCurrency, formatDate, formatPrintedDateTime
 */

// ── Estilos ────────────────────────────────────────────────────────────

export function applyStyles(
  element: HTMLElement,
  styles: Partial<CSSStyleDeclaration>,
) {
  Object.assign(element.style, styles);
}

// ── Imágenes ────────────────────────────────────────────────────────────

export async function waitForImages(root: HTMLElement) {
  const images = Array.from(root.querySelectorAll("img"));
  await Promise.all(
    images.map((img) => {
      if (img.complete) return Promise.resolve();
      return new Promise<void>((resolve) => {
        img.addEventListener("load", () => resolve(), { once: true });
        img.addEventListener("error", () => resolve(), { once: true });
      });
    }),
  );
}

// ── Formato ─────────────────────────────────────────────────────────────

export function formatCurrency(value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return "S/ 0.00";
  return `S/ ${Number(value).toLocaleString("es-PE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("es-PE", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

/** "24 DE JULIO DE 2026 06:30" — fecha + hora en mayúsculas para el PDF */
export function formatPrintedDateTime(isoDatetime: string): string {
  const date = new Date(isoDatetime);
  if (Number.isNaN(date.getTime())) {
    return formatDate(isoDatetime).toUpperCase();
  }
  const dateStr = date
    .toLocaleDateString("es-PE", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    })
    .toUpperCase();
  const timeStr = date.toLocaleTimeString("es-PE", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  return `${dateStr} ${timeStr}`;
}

// ── Filas del recibo ────────────────────────────────────────────────────

/**
 * Agrega una fila label/value al elemento details del PDF.
 * Ej: <div><span>RUC</span><span>20456789012</span></div>
 */
export function appendReceiptRow(
  details: HTMLElement,
  label: string,
  value: string,
) {
  const row = details.ownerDocument.createElement("div");
  row.style.display = "flex";
  row.style.justifyContent = "space-between";
  row.style.padding = "6px 0";
  row.style.borderBottom = "1px solid #e5e7eb";
  row.style.fontSize = "12px";

  const labelEl = details.ownerDocument.createElement("span");
  labelEl.textContent = label;
  labelEl.style.fontWeight = "700";
  labelEl.style.color = "#374151";

  const valueEl = details.ownerDocument.createElement("span");
  valueEl.textContent = value;
  valueEl.style.fontWeight = "500";
  valueEl.style.color = "#111827";
  valueEl.style.textAlign = "right";

  row.appendChild(labelEl);
  row.appendChild(valueEl);
  details.appendChild(row);
}

// ── Frame aislado ───────────────────────────────────────────────────────

export interface PdfFrameResult {
  frame: HTMLIFrameElement;
  frameWindow: Window;
  frameDocument: Document;
}

/**
 * Crea un iframe aislado (off-screen) donde se construye el HTML del PDF.
 * Asegura que el CSS de la app no contamine el documento.
 */
export function createPdfFrame(
  opts: { width?: string; height?: string; position?: string } = {},
): PdfFrameResult {
  const frame = document.createElement("iframe");
  applyStyles(frame, {
    position: opts.position ?? "absolute",
    left: "-10000px",
    top: "0",
    width: opts.width ?? "980px",
    height: opts.height ?? "1123px",
    border: "0",
  });
  document.body.appendChild(frame);

  const frameWindow = frame.contentWindow;
  const frameDocument = frame.contentDocument;
  if (!frameWindow || !frameDocument) {
    frame.remove();
    throw new Error("No se pudo crear el documento aislado para el PDF.");
  }

  frameDocument.open();
  frameDocument.write(
    '<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#FFFFFF;"></body></html>',
  );
  frameDocument.close();

  return { frame, frameWindow, frameDocument };
}
