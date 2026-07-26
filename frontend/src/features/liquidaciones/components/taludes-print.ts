"use client";

/**
 * Taludes-specific print adapter for LiquidacionTaludes.
 *
 * Adapts CrearTaludesResponse (flat list item) to a print-friendly structure
 * and renders a Taludes-specific PDF element (percentage-based).
 *
 * Note: valor_proyecto, porcentaje_liquidacion, porcentaje_minimo_uit are not persisted
 * in the flat response and will show as 0. The percentage fields are user input
 * parameters, not stored in the liquidation record.
 */
import type { CrearTaludesResponse } from "../types/liquidacion-taludes.types";
import type { LiquidacionCardBase } from "../types/liquidacion-general";

// ── Adapter ───────────────────────────────────────────────────────────────────

/**
 * Adapts CrearTaludesResponse to LiquidacionCardBase for use with the
 * generic printLiquidacionDocument() renderer.
 *
 * The Taludes list item already has all required fields compatible with LiquidacionCardBase:
 * - tipo_liquidacion: "taludes"
 * - valores uses ValoresM2ListItem (subtotal, igv, total, total_a_pagar)
 * - revisions[0].tarifa has porcentaje_liquidacion for percentage display
 *
 * This enables the post-create PDF to use the same renderer as the card/list PDF button.
 */
export function TaludesToCardBase(
  created: CrearTaludesResponse,
): LiquidacionCardBase {
  return created as unknown as LiquidacionCardBase;
}

// ── Legacy Adapter ─────────────────────────────────────────────────────────────

export interface TaludesPrintData {
  public_id: string;
  fecha_registro: string;
  expediente: string | null;
  municipalidad_codigo: string | null;
  municipalidad_nombre: string;
  valor_proyecto: number;
  porcentaje_liquidacion: number;
  porcentaje_minimo_uit: number;
  derecho_minimo: number;
  subtotal: number;
  igv: number;
  total: number;
  liquidacion_total: number;
  total_a_pagar: number;
  proyecto_nombre: string;
  proponente_nombre: string;
}

/**
 * Legacy adapter for Taludes-specific PDF print (buildTaludesPdfElement with "TALUDES" header).
 * Use TaludesToCardBase + printLiquidacionDocument() for unified renderer matching card/list.
 */
export function adaptTaludesToPrintData(
  created: CrearTaludesResponse,
): TaludesPrintData {
  const primeraRevision = created.revisiones?.[0];
  const tarifa = primeraRevision?.tarifa;
  return {
    public_id: created.public_id,
    fecha_registro: created.fecha_registro,
    expediente: null, // Not available in Taludes list item (only Edificaciones)
    municipalidad_codigo: created.municipalidad.codigo,
    municipalidad_nombre: created.municipalidad.nombre,
    valor_proyecto: created.proyecto.valor_proyecto,
    porcentaje_liquidacion: tarifa?.porcentaje_liquidacion ?? 0,
    porcentaje_minimo_uit: tarifa?.porcentaje_minimo_uit ?? 0,
    derecho_minimo: tarifa?.derecho_minimo ?? 0,
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

export function formatCurrency(value: number): string {
  return `S/ ${value.toLocaleString("es-PE", { minimumFractionDigits: 2 })}`;
}

/**
 * Builds the "VALOR OBRA: S/ X x Y.YY% = S/ Z" percentage calculation line.
 * porcentaje_liquidacion is a decimal fraction (0.05 = 5%) per backend/domain convention.
 *
 * @param valorObra - The project value (e.g. 100000)
 * @param porcentajeLiquidacion - The decimal fraction (e.g. 0.05 for 5%)
 * @param fmt - Currency formatter (defaults to the module's formatCurrency)
 * @returns The formatted line string, e.g. "VALOR OBRA: S/ 100,000.00 x 5.00% = S/ 5,000.00"
 */
export function formatPorcentajeLine(
  valorObra: number,
  porcentajeLiquidacion: number,
  fmt: (v: number) => string = formatCurrency,
): string {
  const calculated = valorObra * porcentajeLiquidacion;
  const pctDisplay = (porcentajeLiquidacion * 100).toFixed(2);
  return `VALOR OBRA: ${fmt(valorObra)} x ${pctDisplay}% = ${fmt(calculated)}`;
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

export async function printTaludesDocument(data: TaludesPrintData) {
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

    const pdfElement = buildTaludesPdfElement(data, frameDocument);
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

function buildTaludesPdfElement(data: TaludesPrintData, ownerDocument: Document) {
  const {
    public_id,
    fecha_registro,
    expediente,
    municipalidad_codigo,
    municipalidad_nombre,
    valor_proyecto,
    porcentaje_liquidacion,
    porcentaje_minimo_uit,
    derecho_minimo,
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
    "LIQUIDACION DE DERECHOS POR TALUDES",
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
    fontSize: "12px",
    lineHeight: "1.25",
  });
  appendReceiptRow(details, "PROYECTO", proyecto_nombre || "—");
  appendReceiptRow(details, "PROPONENTE", proponente_nombre || "—");
  appendReceiptRow(details, "MUNICIPALIDAD", municipalidad_nombre || "—");
  if (expediente) {
    appendReceiptRow(details, "EXPEDIENTE", expediente);
  }
  // Percentage-based: show Valor de la Obra instead of area
  if (valor_proyecto > 0) {
    appendReceiptRow(details, "VALOR DE LA OBRA", formatCurrency(valor_proyecto));
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

  const calc = append(middle, "div", { fontSize: "12px", lineHeight: "1.5" });
  // Percentage-based calculation line
  // porcentaje_liquidacion is a decimal fraction (0.05 = 5%), per backend/domain convention
  if (valor_proyecto > 0 && porcentaje_liquidacion > 0) {
    appendText(
      calc,
      "p",
      formatPorcentajeLine(valor_proyecto, porcentaje_liquidacion),
      { margin: "0", fontWeight: "700", maxWidth: "620px" },
    );
  }
  if (derecho_minimo > 0) {
    appendText(calc, "p", `Derecho mínimo ${formatCurrency(derecho_minimo)} + IGV ***`, {
      margin: "4px 0 0",
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
