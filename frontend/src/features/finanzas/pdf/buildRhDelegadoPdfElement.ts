/**
 * buildRhDelegadoPdfElement — Compositor de la liquidacion RH Delegado Mensual.
 *
 * Orden: root → paper → header → title → info rows → table → totals → footer
 */
import { applyStyles } from "@/components-app/pdf/pdfShell";
import { formatCurrency, formatPrintedDateTime } from "@/components-app/pdf/pdfShell";
import type { ReciboHonorarioDelegadoMensual } from "@/features/finanzas/schemas/recibo-honorario.schema";

/** Type for style objects — derived from applyStyles to avoid direct CSSStyleDeclaration reference */
type StyleObject = Parameters<typeof applyStyles>[1];

// ── Theme ─────────────────────────────────────────────────────────────────

export const rhPdfTheme = {
  fontFamily: "'Courier New', Courier, monospace",
  fontFamilyDisplay: "Arial, Helvetica, sans-serif",

  colors: {
    ink: "#111827",
    muted: "#4b5563",
    light: "#6b7280",
    paper: "#FFFFFF",
  },

  // Root
  root: {
    position: "absolute",
    left: "-10000px",
    top: "0",
    width: "980px",
    minHeight: "500px",
    backgroundColor: "#FFFFFF",
    color: "#111827",
    fontFamily: "'Courier New', Courier, monospace",
    padding: "14px",
    boxSizing: "border-box",
  } as Partial<CSSStyleDeclaration>,

  // Paper (borde del reporte)
  paper: {
    border: "2px solid #111827",
    borderRadius: "14px",
    padding: "12px 16px",
    minHeight: "455px",
    boxSizing: "border-box",
  } as Partial<CSSStyleDeclaration>,

  // Header grid
  header: {
    display: "grid",
    gridTemplateColumns: "minmax(0, 1fr) 310px",
    gap: "12px",
    alignItems: "start",
  } as Partial<CSSStyleDeclaration>,

  brand: {
    display: "grid",
    gridTemplateColumns: "78px 1fr",
    gap: "14px",
    alignItems: "center",
  } as Partial<CSSStyleDeclaration>,

  logo: {
    width: "70px",
    height: "70px",
    objectFit: "contain",
    display: "block",
  } as Partial<CSSStyleDeclaration>,

  brandTitle: {
    margin: "0",
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "24px",
    fontWeight: "900",
    letterSpacing: "-0.04em",
    lineHeight: "1",
  } as Partial<CSSStyleDeclaration>,

  brandSub: {
    margin: "4px 0 0",
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "16px",
    letterSpacing: "0.04em",
  } as Partial<CSSStyleDeclaration>,

  notice: {
    textAlign: "center",
    fontSize: "14px",
    lineHeight: "1.45",
  } as Partial<CSSStyleDeclaration>,

  noticeLine: {
    margin: "0",
    fontWeight: "800",
    borderBottom: "1px solid #111827",
  } as Partial<CSSStyleDeclaration>,

  title: {
    margin: "12px 0 8px",
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "24px",
    fontWeight: "900",
    letterSpacing: "-0.03em",
    textAlign: "center",
  } as Partial<CSSStyleDeclaration>,

  subtitle: {
    margin: "0 0 12px",
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "16px",
    fontWeight: "700",
    letterSpacing: "0.02em",
    textAlign: "center",
  } as Partial<CSSStyleDeclaration>,

  // Info rows
  infoSection: {
    display: "flex",
    flexDirection: "column",
    gap: "1px",
    fontSize: "19px",
    lineHeight: "1.45",
    marginBottom: "12px",
  } as Partial<CSSStyleDeclaration>,

  // Table
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "11px",
    lineHeight: "1.4",
  } as Partial<CSSStyleDeclaration>,

  th: {
    backgroundColor: "#f3f4f6",
    fontWeight: "700",
    fontSize: "10px",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    padding: "6px 8px",
    border: "1px solid #d1d5db",
    textAlign: "left",
    whiteSpace: "nowrap",
  } as Partial<CSSStyleDeclaration>,

  td: {
    padding: "5px 8px",
    border: "1px solid #d1d5db",
    verticalAlign: "middle",
    fontSize: "11px",
  } as Partial<CSSStyleDeclaration>,

  tdRight: {
    padding: "5px 8px",
    border: "1px solid #d1d5db",
    verticalAlign: "middle",
    fontSize: "11px",
    textAlign: "right",
  } as Partial<CSSStyleDeclaration>,

  tdCenter: {
    padding: "5px 8px",
    border: "1px solid #d1d5db",
    verticalAlign: "middle",
    fontSize: "11px",
    textAlign: "center",
  } as Partial<CSSStyleDeclaration>,

  // Totals row
  totalsRow: {
    fontWeight: "700",
    backgroundColor: "#f9fafb",
  } as Partial<CSSStyleDeclaration>,

  // Footer
  footer: {
    display: "grid",
    gridTemplateColumns: "1fr 1.4fr 1fr",
    gap: "12px",
    alignItems: "end",
    marginTop: "10px",
    fontSize: "15px",
  } as Partial<CSSStyleDeclaration>,

  footerCol: {
    lineHeight: "1.45",
  } as Partial<CSSStyleDeclaration>,

  centerNotice: {
    whiteSpace: "pre-line",
    textAlign: "center",
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "19px",
    fontWeight: "900",
    lineHeight: "1.05",
  } as Partial<CSSStyleDeclaration>,

  // Date/time top-right
  dateTime: {
    textAlign: "right",
    fontSize: "13px",
    fontWeight: "700",
    letterSpacing: "0.06em",
    color: "#111827",
  } as Partial<CSSStyleDeclaration>,
} as const;

// ── DOM Primitives ─────────────────────────────────────────────────────────

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
  styles?: StyleObject,
) {
  const element = append(parent, tagName, styles);
  element.textContent = text;
  return element;
}

function appendReceiptRow(
  parent: HTMLElement,
  label: string,
  value: string,
) {
  const row = append(parent, "div", {
    display: "flex",
    gap: "6px",
    alignItems: "baseline",
  });
  appendText(row, "span", label, {
    fontWeight: "800",
    minWidth: "200px",
    flexShrink: "0",
  });
  appendText(row, "span", `: ${value}`, {
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  });
}

// ── Builder ───────────────────────────────────────────────────────────────

export function buildRhDelegadoPdfElement(
  item: ReciboHonorarioDelegadoMensual,
  ownerDocument: Document,
): HTMLElement {
  const del = item.delegado;
  const totales = item.totales;
  const detalles = item.detalles || [];
  const vc = item.variables_calculo;
  const ctx = item.delegado_operacion_context;

  // Root
  const root = ownerDocument.createElement("div");
  applyStyles(root, rhPdfTheme.root);

  // Paper
  const paper = ownerDocument.createElement("div");
  applyStyles(paper, rhPdfTheme.paper);
  root.appendChild(paper);

  // Header
  const header = append(paper, "div", rhPdfTheme.header);

  // Brand: logo + texto institucional
  const brand = append(header, "div", rhPdfTheme.brand);

  const logo = ownerDocument.createElement("img");
  logo.src = new URL("/images/logo.png", window.location.origin).toString();
  logo.alt = "Logo CIP";
  applyStyles(logo, rhPdfTheme.logo);
  brand.appendChild(logo);

  const brandText = append(brand, "div", { textAlign: "left" });
  appendText(brandText, "h1", "COLEGIO DE INGENIEROS DEL PERU", rhPdfTheme.brandTitle);
  appendText(brandText, "p", "CONSEJO DEPARTAMENTAL DE LIMA", rhPdfTheme.brandSub);
  appendText(brandText, "p", "COMISION DE ASUNTOS MUNICIPALES", {
    ...rhPdfTheme.brandSub,
    margin: "2px 0 0",
  });

  // Notice area (top right) — date/time
  const notice = append(header, "div", rhPdfTheme.notice);
  const printedDateTime = formatPrintedDateTime(item.fecha_registro || "");
  appendText(notice, "p", printedDateTime, rhPdfTheme.dateTime);

  // Title
  appendText(paper, "h2", "LIQUIDACION DE HONORARIOS A DELEGADOS", rhPdfTheme.title);
  appendText(paper, "p", "COMISION TECNICA CALIFICADORA DE PROYECTOS", rhPdfTheme.subtitle);

  // Info rows
  const infoSection = append(paper, "div", rhPdfTheme.infoSection);

  // Row: Municipalidad
  const municipalidad = ctx?.municipalidad_nombre || "—";
  appendReceiptRow(infoSection, "Municipalidad", municipalidad);

  // Row: Delegado CIP + name
  const cipLabel = del?.cip ? `CIP ${del.cip}` : "—";
  const nombreLabel = del?.nombre_completo || "—";
  appendReceiptRow(infoSection, "Delegado", `${cipLabel} — ${nombreLabel}`);

  // Row: Liquidación (blank — header-level number left empty per spec)
  appendReceiptRow(infoSection, "Liquidacion", "");

  // Row: Periodo
  appendReceiptRow(infoSection, "Periodo", item.periodo || "—");

  // Table
  const table = append(paper, "table", rhPdfTheme.table);

  // Header row
  const thead = append(table, "thead", {});
  const headerRow = append(thead, "tr", {});

  const columns = [
    "Nro",
    "F. Rev.",
    "Expdte",
    "Doc. Ref.",
    "Rev",
    "Total",
    "Subtotal",
    "Bruto",
    "CIP",
    "Ap. CODEMU",
    "Fondo",
    "Honorario",
  ];

  for (const col of columns) {
    appendText(headerRow, "th", col, rhPdfTheme.th);
  }

  // Body rows
  const tbody = append(table, "tbody", {});
  for (const detalle of detalles) {
    const tr = append(tbody, "tr", {});

    // Nro — liquidacion_especifica_numero fallback "—"
    const nro = detalle.liquidacion_especifica_numero != null
      ? String(detalle.liquidacion_especifica_numero)
      : "—";
    appendText(tr, "td", nro, rhPdfTheme.tdCenter);

    // F. Rev.
    const fechaRev = detalle.fecha_revision
      ? new Date(detalle.fecha_revision).toLocaleDateString("es-PE", {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
        })
      : "—";
    appendText(tr, "td", fechaRev, rhPdfTheme.td);

    // Expdte
    appendText(tr, "td", detalle.expediente || "—", rhPdfTheme.td);

    // Doc. Ref. — serie + numero from comprobante_activo
    let docRef = "—";
    if (detalle.comprobante_activo?.serie && detalle.comprobante_activo?.numero) {
      docRef = `${detalle.comprobante_activo.serie}-${detalle.comprobante_activo.numero}`;
    }
    appendText(tr, "td", docRef, rhPdfTheme.tdCenter);

    // Rev (numero_revision)
    appendText(tr, "td", detalle.numero_revision != null ? String(detalle.numero_revision) : "—", rhPdfTheme.tdCenter);

    // Total
    appendText(tr, "td", detalle.total_liquidacion != null ? formatCurrency(detalle.total_liquidacion) : "—", rhPdfTheme.tdRight);

    // Subtotal
    appendText(tr, "td", detalle.sub_total_liquidacion != null ? formatCurrency(detalle.sub_total_liquidacion) : "—", rhPdfTheme.tdRight);

    // Bruto
    appendText(tr, "td", formatCurrency(detalle.imp_bruto), rhPdfTheme.tdRight);

    // CIP (renta_cip)
    appendText(tr, "td", detalle.renta_cip != null ? formatCurrency(detalle.renta_cip) : "—", rhPdfTheme.tdRight);

    // Ap. CODEMU
    appendText(tr, "td", detalle.aporte_codemu != null ? formatCurrency(detalle.aporte_codemu) : "—", rhPdfTheme.tdRight);

    // Fondo
    appendText(tr, "td", detalle.fondo_comun != null ? formatCurrency(detalle.fondo_comun) : "—", rhPdfTheme.tdRight);

    // Honorario (neto_honorario)
    appendText(tr, "td", detalle.neto_honorario != null ? formatCurrency(detalle.neto_honorario) : "—", rhPdfTheme.tdRight);
  }

  // Totals row
  const totalsTr = append(tbody, "tr", rhPdfTheme.totalsRow);
  appendText(totalsTr, "td", "TOTALES", { ...rhPdfTheme.td, fontWeight: "700", textAlign: "right" });
  appendText(totalsTr, "td", "", rhPdfTheme.td);
  appendText(totalsTr, "td", "", rhPdfTheme.td);
  appendText(totalsTr, "td", "", rhPdfTheme.td);
  appendText(totalsTr, "td", "", rhPdfTheme.td);
  appendText(totalsTr, "td", formatCurrency(
    detalles.reduce((sum, d) => sum + (d.total_liquidacion ?? 0), 0),
  ), rhPdfTheme.tdRight);
  appendText(totalsTr, "td", formatCurrency(
    detalles.reduce((sum, d) => sum + (d.sub_total_liquidacion ?? 0), 0),
  ), rhPdfTheme.tdRight);
  appendText(totalsTr, "td", formatCurrency(
    detalles.reduce((sum, d) => sum + (d.imp_bruto ?? 0), 0),
  ), rhPdfTheme.tdRight);
  appendText(totalsTr, "td", formatCurrency(totales.renta_cip), rhPdfTheme.tdRight);
  appendText(totalsTr, "td", formatCurrency(totales.aporte_codemu), rhPdfTheme.tdRight);
  appendText(totalsTr, "td", formatCurrency(totales.fondo_comun), rhPdfTheme.tdRight);
  appendText(totalsTr, "td", formatCurrency(totales.neto_honorario), { ...rhPdfTheme.tdRight, fontWeight: "700", color: "#111827" });

  // Footer
  const footer = append(paper, "div", rhPdfTheme.footer);

  const left = append(footer, "div", rhPdfTheme.footerCol);
  appendText(left, "p", "COMISION DE ASUNTOS MUNICIPALES", {
    margin: "0",
    fontSize: "13px",
    fontWeight: "800",
  });
  appendText(left, "p", "Tel.: 202-5066", { margin: "0", fontSize: "13px" });
  appendText(left, "p", `Elaborado por ${del?.nombre_completo || "—"}`, {
    margin: "8px 0 0",
    fontWeight: "700",
  });
  appendText(left, "p", printedDateTime, {
    margin: "16px 0 0",
    letterSpacing: "0.08em",
    fontWeight: "700",
  });

  appendText(
    footer,
    "div",
    "REPORTE DE LIQUIDACION\nPARA CONTROL INTERNO",
    rhPdfTheme.centerNotice,
  );

  const right = append(footer, "div", { lineHeight: "1.45" });
  appendText(right, "p", `Neto a Pagar`, { margin: "0", fontWeight: "700" });
  appendText(right, "p", formatCurrency(totales.neto_honorario), {
    margin: "4px 0 0",
    fontSize: "22px",
    fontWeight: "900",
    letterSpacing: "0.04em",
  });

  return root;
}
