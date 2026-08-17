/**
 * pdfSections — Secciones del recibo oficial (composición).
 * Cada sección construye UNA parte del recibo con (doc, item, tipo, theme).
 * El compositor (buildLiquidacionPdfElement) las une en orden.
 */
import {
  applyStyles,
  formatCurrency,
  formatPrintedDateTime,
} from "@/components-app/pdf/pdfShell";
import type {
  PdfLiquidacionItem,
  PdfMotor,
} from "./buildLiquidacionPdfElement";
import { getPdfTitleByTipo } from "./buildLiquidacionPdfElement";
import { pdfTheme } from "./pdfTheme";

// ── Primitivas DOM ────────────────────────────────────────────────────────

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

export function appendReceiptRow(
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

export function appendTotalLine(
  parent: HTMLElement,
  label: string,
  value: string,
) {
  const row = append(parent, "div", {
    display: "grid",
    gridTemplateColumns: "1fr auto",
    gap: "12px",
  });
  appendText(row, "span", label, { fontWeight: "700" });
  appendText(row, "span", value);
}

function sinMoneda(value: string): string {
  return value.replace("S/ ", "");
}

// ── Header: logo + institución + notice ───────────────────────────────────

export function renderHeader(paper: HTMLElement, item: PdfLiquidacionItem) {
  const doc = paper.ownerDocument;
  const lg = item.liquidacion_general;

  const header = append(paper, "div", pdfTheme.header);

  // Brand: logo + texto institucional
  const brand = append(header, "div", pdfTheme.brand);

  const logo = doc.createElement("img");
  logo.src = new URL("/images/logo.png", window.location.origin).toString();
  logo.alt = "Logo CIP";
  applyStyles(logo, pdfTheme.logo);
  brand.appendChild(logo);

  const brandText = append(brand, "div", { textAlign: "left" });
  appendText(
    brandText,
    "h1",
    "COLEGIO DE INGENIEROS DEL PERU",
    pdfTheme.brandTitle,
  );
  appendText(
    brandText,
    "p",
    "CONSEJO DEPARTAMENTAL DE LIMA",
    pdfTheme.brandSub,
  );
  appendText(brandText, "p", "COMISION DE ASUNTOS MUNICIPALES", {
    ...pdfTheme.brandSub,
    margin: "2px 0 0",
  });

  // Notice: IMPORTANTE + CTA + código + Nro (solo el número correlativo de la especialidad)
  const notice = append(header, "div", pdfTheme.notice);
  appendText(
    notice,
    "p",
    "IMPORTANTE: ESTA LIQUIDACION DEBERA",
    pdfTheme.noticeLine,
  );
  appendText(notice, "p", "ADJUNTARLA AL COMPROBANTE DE PAGO", {
    ...pdfTheme.noticeLine,
    margin: "8px 0 0",
  });
  appendText(notice, "p", "CTA 46201", {
    margin: "6px 0 0",
    fontSize: "24px",
    fontWeight: "700",
    letterSpacing: "0.12em",
  });
  appendText(notice, "p", `Codigo de Pago ${lg.municipalidad?.codigo || "—"}`, {
    margin: "2px 0 0",
    fontSize: "13px",
  });
  appendText(
    notice,
    "p",
    `Nro: ${item.liquidacion_especifica?.numero ?? "—"}`,
    {
      margin: "10px 0 0",
      fontSize: "18px",
      letterSpacing: "0.08em",
      overflowWrap: "anywhere",
    },
  );
}

// ── Título oficial ────────────────────────────────────────────────────────

export function renderTitle(paper: HTMLElement, tipo: string) {
  appendText(paper, "h2", getPdfTitleByTipo(tipo), pdfTheme.title);
}

// ── Detalle: campos comunes + específicos por motor ───────────────────────

function appendCommonFields(details: HTMLElement, item: PdfLiquidacionItem) {
  const lg = item.liquidacion_general;
  const proyecto = lg.proyecto;
  const entidad = proyecto.entidad;
  appendReceiptRow(details, "RUC", entidad?.numero_documento || "—");
  appendReceiptRow(details, "RAZON SOCIAL", entidad?.razon_social || "—");
  appendReceiptRow(
    details,
    "NOMBRE DEL PROPIETARIO",
    proyecto.nombre_propietario || entidad?.razon_social || "—",
  );
  appendReceiptRow(
    details,
    "NOMBRE DEL PROYECTO",
    proyecto.denominacion || "—",
  );
  appendReceiptRow(
    details,
    "DPTO. / PROV. / DISTRITO",
    lg.municipalidad?.nombre || "—",
  );
  appendReceiptRow(details, "DIRECCION DE LA OBRA", proyecto.direccion || "—");
}

function renderSpecificByMotor(
  motor: PdfMotor,
  specificFields: HTMLElement,
  item: PdfLiquidacionItem,
) {
  const lt = item.liquidacion_tipo;

  if (motor === "m2") {
    if (lt.area_m2 && lt.area_m2 > 0) {
      appendReceiptRow(
        specificFields,
        "AREA",
        `${Number(lt.area_m2).toLocaleString("es-PE")} m²`,
      );
    }
    if (lt.costo_por_m2 && lt.costo_por_m2 > 0) {
      appendReceiptRow(
        specificFields,
        "COSTO POR M2",
        formatCurrency(lt.costo_por_m2),
      );
    }
    return;
  }

  if (motor === "visitas") {
    if (lt.cantidad_visitas && lt.cantidad_visitas > 0) {
      appendReceiptRow(
        specificFields,
        "CANTIDAD DE VISITAS",
        `${lt.cantidad_visitas}`,
      );
    }
    if (lt.categoria) {
      appendReceiptRow(specificFields, "CATEGORIA", lt.categoria);
    }
    const inspector = lt.inspectores?.[0];
    const perfil = inspector?.perfil_ingeniero;
    if (perfil?.nombre_completo) {
      appendReceiptRow(specificFields, "INSPECTOR", perfil.nombre_completo);
    }
    if (perfil?.cip) {
      appendReceiptRow(specificFields, "CIP", perfil.cip);
    }
    return;
  }

  // porcentaje
  if (lt.valor_declarado && lt.valor_declarado > 0) {
    appendReceiptRow(
      specificFields,
      "VALOR DE OBRA",
      formatCurrency(lt.valor_declarado),
    );
  }
  if (lt.porcentaje_liquidacion != null) {
    const pctDisplay = (Number(lt.porcentaje_liquidacion) * 100).toFixed(2);
    appendReceiptRow(specificFields, "PORCENTAJE", `${pctDisplay}%`);
  }
}

export function renderDetalle(
  paper: HTMLElement,
  item: PdfLiquidacionItem,
  motor: PdfMotor,
) {
  const details = append(paper, "div", pdfTheme.details);
  appendCommonFields(details, item);

  const lowerBody = append(paper, "div", pdfTheme.lowerBody);

  const specificFields = append(lowerBody, "div", pdfTheme.specificFields);
  renderSpecificByMotor(motor, specificFields, item);

  // Derecho mínimo + IGV (si > 0)
  const derechoMinimo = item.liquidacion_tipo.derecho_minimo ?? 0;
  if (derechoMinimo > 0) {
    appendReceiptRow(
      specificFields,
      "DERECHO MINIMO",
      `${formatCurrency(derechoMinimo)} + IGV`,
    );
  }

  // Montos — datos REALES del backend
  const lg = item.liquidacion_general;
  const subTotal = lg.sub_total ?? 0;
  const total = lg.total ?? 0;
  // IGV solo se muestra si subtotal y total difieren (hay IGV aplicado).
  // Si subtotal === total → no hay IGV → se omite la línea (visual solamente).
  const igvMonto = total - subTotal;
  const tieneIgv = total !== subTotal && igvMonto > 0;

  const totals = append(lowerBody, "div", pdfTheme.totals);
  appendTotalLine(totals, "SUBTOTAL S/.", sinMoneda(formatCurrency(subTotal)));
  if (tieneIgv) {
    appendTotalLine(totals, "I.G.V. S/.", sinMoneda(formatCurrency(igvMonto)));
  }
  const totalBox = append(totals, "div", pdfTheme.totalBox);
  appendText(totalBox, "span", "TOTAL S/.", {
    fontWeight: "700",
    fontSize: "15px",
  });
  appendText(totalBox, "span", sinMoneda(formatCurrency(total)), {
    fontWeight: "700",
    fontSize: "15px",
  });
}

// ── Total a pagar grande ──────────────────────────────────────────────────

export function renderTotalPagar(paper: HTMLElement, item: PdfLiquidacionItem) {
  const lg = item.liquidacion_general;
  const pay = append(paper, "div", pdfTheme.pay);
  append(pay, "div");
  appendText(
    pay,
    "div",
    `TOTAL A PAGAR S/. ${sinMoneda(formatCurrency(lg.total))}`,
    pdfTheme.totalPagar,
  );
  append(pay, "div");
}

// ── Footer ────────────────────────────────────────────────────────────────

export function renderFooter(paper: HTMLElement, item: PdfLiquidacionItem) {
  const lg = item.liquidacion_general;
  const printedDateTime = formatPrintedDateTime(lg.fecha_registro || "");
  const contactoNombre =
    lg.proyecto.nombre_propietario || lg.proyecto.entidad?.razon_social || "—";
  const hechoPor = lg.usuario_creador
    ? [lg.usuario_creador.nombres, lg.usuario_creador.apellidos]
        .filter(Boolean)
        .join(" ") ||
      lg.usuario_creador.username ||
      "—"
    : "—";

  const footer = append(paper, "div", pdfTheme.footer);

  const left = append(footer, "div", pdfTheme.footerCol);
  appendText(left, "p", "COMISION DE ASUNTOS MUNICIPALES", {
    margin: "0",
    fontSize: "13px",
    fontWeight: "800",
  });
  appendText(left, "p", "Tel.: 202-5066", { margin: "0", fontSize: "13px" });
  appendText(left, "p", `Tramitado por ${contactoNombre}`, {
    margin: "8px 0 0",
    fontWeight: "700",
  });
  appendText(left, "p", "TELEFONO      —", {
    margin: "10px 0 0",
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
    "ESTE DOCUMENTO NO ES\nCOMPROBANTE DE PAGO",
    pdfTheme.noComprobante,
  );

  const right = append(footer, "div", { lineHeight: "1.45" });
  appendText(right, "p", `Hecho por ${hechoPor}`, { margin: "0" });
  appendText(right, "p", printedDateTime, { margin: "12px 0 0" });
}
