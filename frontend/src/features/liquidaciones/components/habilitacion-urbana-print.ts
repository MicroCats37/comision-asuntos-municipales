"use client";

/**
 * HU-specific print adapter for LiquidacionHabilitacionUrbana.
 *
 * Adapts CrearHabilitacionUrbanaResponse to a print-friendly structure
 * and renders an HU-specific PDF element (area-based, NOT percentage-based).
 *
 * Key differences from Edificaciones print:
 * - Shows area_solicitada, costo_por_m2, derecho_min/max instead of valor_proyecto × percentage
 * - Uses m² units throughout
 * - No "Valor de la Obra" label (HU doesn't have this field)
 */

import type { CrearHabilitacionUrbanaResponse } from "../types/liquidacion-habilitacion-urbana.types";
import type { LiquidacionCardBase } from "../types/liquidacion-general";

// ── CardBase Adapter ─────────────────────────────────────────────────────────────

/**
 * Adapts CrearHabilitacionUrbanaResponse to LiquidacionCardBase for use with the
 * generic printLiquidacionDocument() renderer.
 *
 * The HU list item is structurally compatible with LiquidacionCardBase:
 * - tipo_liquidacion: "habilitacion-urbana"
 * - valores uses ValoresM2ListItem (subtotal, igv, total, total_a_pagar)
 * - revisions[0].tarifa has area_solicitada/costo_por_m2 for m² display
 *
 * This enables the post-create PDF to use the same renderer as the card/list PDF button.
 */
export function HUToCardBase(
  created: CrearHabilitacionUrbanaResponse,
): LiquidacionCardBase {
  return created as unknown as LiquidacionCardBase;
}

// ── Legacy Print Adapter ─────────────────────────────────────────────────────────

/**
 * HU print data extracted from the flat create response.
 * All numeric fields default to 0 for graceful fallback when calculation data
 * (area_solicitada, costo_por_m2) is not persisted in the flat structure.
 */
export interface HuPrintData {
  public_id: string;
  fecha_registro: string;
  expediente: string | null;
  municipalidad_codigo: string | null;
  municipalidad_nombre: string;
  /** Area in m² from the cotizacion — not persisted in flat response, shows 0 */
  area_solicitada: number;
  /** costo_por_m2 from tariff — not persisted in flat response, shows 0 */
  costo_por_m2: number;
  /** derecho_minimo from tariff */
  derecho_minimo: number;
  /** derecho_maximo from tariff (nullable) */
  derecho_maximo: number | null;
  subtotal: number;
  igv: number;
  total: number;
  liquidacion_total: number;
  total_a_pagar: number;
  /** Proponente / entity name */
  proponente_nombre: string;
  /** Project name (denominacion) */
  proyecto_nombre: string;
}

export function adaptHuToPrintData(
  created: CrearHabilitacionUrbanaResponse,
): HuPrintData {
  const primeraRevision = created.revisiones?.[0];
  const tarifa = primeraRevision?.tarifa;
  return {
    public_id: created.public_id,
    fecha_registro: created.fecha_registro,
    expediente: null, // Not available in HU list item (only Edificaciones)
    municipalidad_codigo: created.municipalidad.codigo,
    municipalidad_nombre: created.municipalidad.nombre,
    // area_solicitada comes from user's input, NOT from tariff metadata
    area_solicitada: tarifa?.area_solicitada ?? 0,
    costo_por_m2: tarifa?.costo_por_m2 ?? 0,
    derecho_minimo: tarifa?.derecho_minimo ?? 0,
    derecho_maximo: tarifa?.derecho_maximo ?? null,
    subtotal: created.valores.subtotal,
    igv: created.valores.igv,
    total: created.valores.total,
    liquidacion_total: created.valores.total_a_pagar,
    total_a_pagar: created.valores.total_a_pagar,
    proyecto_nombre: created.proyecto.nombre,
    proponente_nombre: created.entidad?.nombre ?? "—",
  };
}

// ── Print ─────────────────────────────────────────────────────────────────────

function formatCurrency(value: number): string {
  return `S/ ${value.toLocaleString("es-PE", { minimumFractionDigits: 2 })}`;
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return dateStr.toUpperCase();
  return date.toLocaleDateString("es-PE", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).toUpperCase();
}

export async function printHabilitacionUrbanaDocument(data: HuPrintData) {
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
      `<!doctype html><html><head><meta charset="utf-8"><title>${data.public_id}</title></head><body style="margin:0;background:#FFFFFF;"></body></html>`,
    );
    frameDocument.close();

    const pdfElement = buildHuPdfElement(data, frameDocument);
    applyStyles(pdfElement, {
      position: "static",
      left: "auto",
      top: "auto",
      width: "980px",
      margin: "0 auto",
    });
    frameDocument.body.appendChild(pdfElement);

    await waitForImages(pdfElement);
    frameWindow.focus();
    frameWindow.print();

    setTimeout(() => frame.remove(), 1000);
  } catch (err) {
    frame.remove();
    throw err;
  }
}

function buildHuPdfElement(data: HuPrintData, ownerDocument: Document) {
  const {
    public_id,
    fecha_registro,
    expediente,
    municipalidad_codigo,
    municipalidad_nombre,
    area_solicitada,
    costo_por_m2,
    derecho_minimo,
    derecho_maximo,
    subtotal,
    igv,
    total,
    liquidacion_total,
    total_a_pagar,
    proyecto_nombre,
    proponente_nombre,
  } = data;

  const root = ownerDocument.createElement("div");
  const printedDate = formatDate(fecha_registro);

  applyStyles(root, {
    position: "absolute",
    left: "-10000px",
    top: "0",
    width: "980px",
    minHeight: "500px",
    backgroundColor: "#FFFFFF",
    color: "#111827",
    fontFamily: "'Courier New', Courier, monospace",
    padding: "18px",
    boxSizing: "border-box",
  });

  const paper = append(root, "div", {
    border: "2px solid #111827",
    borderRadius: "14px",
    padding: "14px 18px",
    minHeight: "455px",
    boxSizing: "border-box",
  });

  // Header
  const header = append(paper, "div", {
    display: "grid",
    gridTemplateColumns: "minmax(0, 1fr) 330px",
    gap: "18px",
    alignItems: "start",
  });

  const brand = append(header, "div", {
    display: "grid",
    gridTemplateColumns: "78px 1fr",
    gap: "14px",
    alignItems: "center",
  });

  const logo = ownerDocument.createElement("img");
  logo.src = new URL("/images/logo.png", window.location.origin).toString();
  logo.alt = "Logo CIP";
  applyStyles(logo, {
    width: "70px",
    height: "70px",
    objectFit: "contain",
    display: "block",
  });
  brand.appendChild(logo);

  const brandText = append(brand, "div", { textAlign: "left" });
  appendText(brandText, "h1", "COLEGIO DE INGENIEROS DEL PERU", {
    margin: "0",
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "24px",
    fontWeight: "900",
    letterSpacing: "-0.04em",
    lineHeight: "1",
  });
  appendText(brandText, "p", "CONSEJO DEPARTAMENTAL DE LIMA", {
    margin: "4px 0 0",
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "16px",
    letterSpacing: "0.04em",
  });
  appendText(brandText, "p", "COMISION DE ASUNTOS MUNICIPALES", {
    margin: "2px 0 0",
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "16px",
    letterSpacing: "0.04em",
  });

  const notice = append(header, "div", {
    textAlign: "center",
    fontSize: "12px",
    lineHeight: "1.35",
  });
  appendText(notice, "p", "IMPORTANTE: ESTA LIQUIDACION DEBERA", {
    margin: "0",
    fontWeight: "700",
    borderBottom: "1px solid #111827",
  });
  appendText(notice, "p", "ADJUNTARLA AL COMPROBANTE DE PAGO", {
    margin: "8px 0 0",
    fontWeight: "700",
    borderBottom: "1px solid #111827",
  });
  appendText(notice, "p", "CTA 46201", {
    margin: "6px 0 0",
    fontSize: "20px",
    fontWeight: "700",
    letterSpacing: "0.12em",
  });
  appendText(notice, "p", `Codigo de Pago ${municipalidad_codigo || "—"}`, {
    margin: "2px 0 0",
    fontSize: "11px",
  });
  appendText(notice, "p", `Nro: ${public_id}`, {
    margin: "10px 0 0",
    fontSize: "15px",
    letterSpacing: "0.08em",
    overflowWrap: "anywhere",
  });

  appendText(
    paper,
    "h2",
    "LIQUIDACION DE DERECHOS POR HABILITACION URBANA",
    {
      margin: "12px 0 8px",
      fontFamily: "Arial, Helvetica, sans-serif",
      fontSize: "18px",
      fontWeight: "900",
      letterSpacing: "-0.03em",
    },
  );

  // Details
  const details = append(paper, "div", {
    display: "grid",
    gridTemplateColumns: "245px 1fr",
    gap: "3px 12px",
    fontSize: "14px",
    lineHeight: "1.25",
  });
  appendReceiptRow(details, "PROYECTO", proyecto_nombre || "—");
  appendReceiptRow(details, "PROPONENTE", proponente_nombre || "—");
  appendReceiptRow(details, "MUNICIPALIDAD", municipalidad_nombre || "—");
  if (expediente) {
    appendReceiptRow(details, "EXPEDIENTE", expediente);
  }
  // HU-specific: area instead of valor de obra
  appendReceiptRow(details, "AREA SOLICITADA", `${area_solicitada.toLocaleString("es-PE")} m²`);
  if (costo_por_m2 > 0) {
    appendReceiptRow(details, "COSTO POR M2", formatCurrency(costo_por_m2));
  }

  // Middle section: calculation breakdown
  const middle = append(
    paper,
    "div",
    {
      display: "grid",
      gridTemplateColumns: "1fr 260px",
      gap: "22px",
      marginTop: "18px",
      alignItems: "start",
    },
  );

  const calc = append(middle, "div", { fontSize: "14px", lineHeight: "1.5" });
  if (area_solicitada > 0 && costo_por_m2 > 0) {
    appendText(
      calc,
      "p",
      `AREA: ${area_solicitada.toLocaleString("es-PE")} m² x ${formatCurrency(costo_por_m2)}/m²`,
      { margin: "0", fontWeight: "700", maxWidth: "620px" },
    );
  }
  appendText(calc, "p", `Derecho mínimo ${formatCurrency(derecho_minimo)} + IGV ***`, {
    margin: "4px 0 0",
  });
  if (derecho_maximo != null) {
    appendText(calc, "p", `Derecho máximo ${formatCurrency(derecho_maximo)}`, {
      margin: "2px 0 0",
    });
  }

  const totals = append(middle, "div", { fontSize: "12px", lineHeight: "1.55" });
  appendTotalLine(totals, "SUBTOTAL S/.", formatCurrency(subtotal).replace("S/ ", ""));
  appendTotalLine(totals, "I.G.V. S/.", formatCurrency(igv).replace("S/ ", ""));
  appendTotalLine(totals, "TOTAL S/.", formatCurrency(total).replace("S/ ", ""));
  const totalBox = append(totals, "div", {
    display: "grid",
    gridTemplateColumns: "1fr auto",
    gap: "12px",
    border: "1px solid #111827",
    borderRadius: "10px",
    padding: "2px 6px",
    marginTop: "4px",
  });
  appendText(totalBox, "span", "TOTAL S/.", { fontWeight: "700" });
  appendText(totalBox, "span", formatCurrency(liquidacion_total).replace("S/ ", ""));

  // Total a pagar
  const pay = append(paper, "div", {
    display: "grid",
    gridTemplateColumns: "1fr auto 1fr",
    alignItems: "center",
    gap: "16px",
    marginTop: "18px",
  });
  append(pay, "div");
  appendText(
    pay,
    "div",
    `TOTAL A PAGAR S/. ${formatCurrency(total_a_pagar).replace("S/ ", "")}`,
    {
      textAlign: "center",
      fontSize: "24px",
      fontWeight: "700",
      letterSpacing: "0.08em",
    },
  );
  append(pay, "div");

  // Footer
  const footer = append(
    paper,
    "div",
    {
      display: "grid",
      gridTemplateColumns: "270px 1fr 210px",
      gap: "16px",
      alignItems: "end",
      marginTop: "16px",
      fontSize: "12px",
    },
  );
  const left = append(footer, "div", { lineHeight: "1.35" });
  appendText(left, "p", "COMISION DE ASUNTOS MUNICIPALES", {
    margin: "0",
    fontSize: "10px",
    fontWeight: "700",
  });
  appendText(left, "p", "Tel.: 202-5066", { margin: "0", fontSize: "10px" });
  appendText(left, "p", "Tramitado por —", { margin: "8px 0 0" });
  appendText(left, "p", "TELEFONO      —", { margin: "10px 0 0" });
  appendText(left, "p", printedDate, { margin: "16px 0 0", letterSpacing: "0.08em" });

  appendText(
    footer,
    "div",
    "ESTE DOCUMENTO NO ES\nCOMPROBANTE DE PAGO",
    {
      whiteSpace: "pre-line",
      textAlign: "center",
      fontFamily: "Arial, Helvetica, sans-serif",
      fontSize: "19px",
      fontWeight: "900",
      lineHeight: "1.05",
    },
  );

  const right = append(footer, "div", { lineHeight: "1.45" });
  appendText(right, "p", "Hecho por —", { margin: "0" });
  appendText(right, "p", new Date().toLocaleTimeString("es-PE", { hour12: false }), {
    margin: "12px 0 0",
  });

  return root;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function appendReceiptRow(parent: HTMLElement, label: string, value: string) {
  appendText(parent, "span", label, { fontWeight: "700" });
  appendText(parent, "span", `: ${value}`, {
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  });
}

function appendTotalLine(parent: HTMLElement, label: string, value: string) {
  const row = append(parent, "div", {
    display: "grid",
    gridTemplateColumns: "1fr auto",
    gap: "12px",
  });
  appendText(row, "span", label, { fontWeight: "700" });
  appendText(row, "span", value);
}

function append<T extends keyof HTMLElementTagNameMap>(
  parent: HTMLElement,
  tagName: T,
  styles?: Partial<CSSStyleDeclaration>,
) {
  const element = parent.ownerDocument.createElement(tagName);
  if (styles) applyStyles(element, styles);
  parent.appendChild(element);
  return element;
}

function appendText<T extends keyof HTMLElementTagNameMap>(
  parent: HTMLElement,
  tagName: T,
  text: string,
  styles?: Partial<CSSStyleDeclaration>,
) {
  const element = append(parent, tagName, styles);
  element.textContent = text;
  return element;
}

function applyStyles(
  element: HTMLElement,
  styles: Partial<CSSStyleDeclaration>,
) {
  Object.assign(element.style, styles);
}

async function waitForImages(root: HTMLElement) {
  const images = Array.from(root.querySelectorAll("img"));
  await Promise.all(
    images.map(
      (img) =>
        new Promise<void>((resolve) => {
          if (img.complete) {
            resolve();
            return;
          }
          img.onload = () => resolve();
          img.onerror = () => resolve();
        }),
    ),
  );
}
