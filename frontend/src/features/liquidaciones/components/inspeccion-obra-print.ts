"use client";

/**
 * IO-specific print adapter for LiquidacionInspeccionObra.
 *
 * Adapts CrearInspeccionObraResponse (flat list item) to a print-friendly structure
 * and renders an IO-specific PDF element (visitas-based, NOT area-based).
 *
 * Key differences from HU/MS/IV/Taludes print:
 * - Shows cantidad_visitas and categoria instead of area_solicitada
 * - Shows costo_por_visita × visitas instead of area × costo_por_m2
 * - Uses visitas units throughout
 * - Does NOT show m² labels (wrong for IO)
 *
 * Note: The flat list item has visitas data in revisiones[0].tarifa.
 * cotizacion is no longer needed at create time — all needed data
 * is persisted in the LiquidacionInspeccionObra record.
 */
import type { CrearInspeccionObraResponse } from "../types/liquidacion-inspeccion-obra.types";

// ── Adapter ───────────────────────────────────────────────────────────────────

/**
 * IO-specific print data structure.
 * All numeric fields default to 0 for graceful fallback when backend
 * response lacks full breakdown data.
 */
/** Current user info from session for PDF attribution */
export interface PdfCurrentUser {
  nombres: string | null;
  apellidos: string | null;
}

export interface IOPPrintData {
  public_id: string;
  fecha_registro: string;
  expediente: string | null;
  municipalidad_codigo: string | null;
  municipalidad_nombre: string;
  /** RUC from entidad */
  ruc: string | null;
  /** Razon social from entidad */
  razon_social: string | null;
  /** Nombre del propietario (contacto principal or proyecto nombre) */
  nombre_propietario: string | null;
  /** Dpto / Prov / Distrito from municipalidad */
  departamento: string | null;
  /** Direccion de la obra from proyecto */
  direccion: string | null;
  /** Cantidad de visitas / numero de supervisiones */
  cantidad_visitas: number;
  /** Categoria from cotizacion */
  categoria: string;
  /** CIP y nombre del delegado supervisor */
  cip_delegado: string | null;
  /** Valor vigente de la UIT — not persisted in list item, shown blank */
  uit_valor: string | null;
  /** Monto equivalente a 1 supervision — not persisted, shown blank */
  monto_equivalente: string | null;
  /** Porcentaje a aplicar sobre la UIT — not persisted, shown blank */
  porcentaje_aplicar: string | null;
  /** Costo por visita from tariff */
  costo_por_visita: number;
  /** Visitas minimas from tariff */
  visitas_minimas: number;
  /** Derecho (total derecho) — equals subtotal for IO */
  derecho: number;
  subtotal: number;
  igv: number;
  total: number;
  liquidacion_total: number;
  total_a_pagar: number;
  /** Inspector CIP number (kept for calc section fallback) */
  inspector_cip: string | null;
  /** Inspector full name (nombres + apellidos) (kept for calc section fallback) */
  inspector_nombre: string | null;
  /** Person who processed the liquidation — first contacto full name (not session user) */
  tramitado_por: string | null;
  /** Contact phone number */
  telefono: string | null;
  /** Person who printed/generated this document — session user */
  hecho_por: string | null;
}

/**
 * Adapt from flat CrearInspeccionObraResponse (LiquidacionInspeccionObraListItem).
 * Reads visitas data from revisiones[0].tarifa, valores from flat structure.
 * Extracts inspector and contact data for post-create PDF.
 *
 * @param created - The created IO response from backend
 * @param currentUser - Optional current session user; if provided, takes priority for
 *                     tramitado_por and hecho_por fields over contact fallback.
 */
export function adaptIOToPrintData(
  created: CrearInspeccionObraResponse,
  currentUser?: PdfCurrentUser,
): IOPPrintData {
  const primeraRevision = created.revisiones?.[0];
  const tarifa = primeraRevision?.tarifa;

  // Get first inspector if available
  const inspector = created.inspectores?.[0];
  const inspectorCip = inspector?.perfil_ingeniero_cip ?? null;
  const inspectorNombre = inspector
    ? `${inspector.perfil_ingeniero_nombres ?? ''} ${inspector.perfil_ingeniero_apellidos ?? ''}`.trim()
    : null;

  // Session user display name for tramitado_por and hecho_por
  const sessionUserDisplayName = currentUser
    ? `${currentUser.nombres ?? ''} ${currentUser.apellidos ?? ''}`.trim()
    : null;

  // First contacto (principal first, then any available)
  const contacto = created.contactos?.find(c => c.principal) ?? created.contactos?.[0];

  // telefono: first contacto phone, fallback '—'
  const telefono = contacto?.telefono ?? contacto?.celular ?? null;

  // tramitado_por: first contacto full name, fallback '—' (NOT session user)
  const tramitadoPor = contacto
    ? `${contacto.nombres ?? ''} ${contacto.apellidos ?? ''}`.trim()
    : null;

  // hecho_por: session user only (document creator per spec)
  const hechoPor = sessionUserDisplayName;

  // Proponente / razon social from entidad
  const razonSocial = created.entidad?.nombre ?? null;

  // Owner / propietario: contacto principal first, then proyecto nombre
  const nombrePropietario = contacto
    ? `${contacto.nombres ?? ''} ${contacto.apellidos ?? ''}`.trim()
    : created.proyecto?.nombre ?? null;

  // CIP y nombre del delegado supervisor
  const cipDelegado = inspectorCip && inspectorNombre
    ? `${inspectorCip} - ${inspectorNombre}`
    : inspectorCip
    ? `${inspectorCip}`
    : inspectorNombre
    ? inspectorNombre
    : null;

  // UIT/monto/% fields are not persisted in LiquidacionInspeccionObraListItem — show blank labels
  const uitValor = null;
  const montoEquivalente = null;
  const porcentajeAplicar = null;

  return {
    public_id: created.public_id,
    fecha_registro: created.fecha_registro,
    expediente: null, // Not available in IO list item (only Edificaciones)
    municipalidad_codigo: created.municipalidad.codigo,
    municipalidad_nombre: created.municipalidad.nombre,
    ruc: created.entidad?.ruc ?? created.proyecto?.entidad?.ruc ?? null,
    razon_social: razonSocial,
    nombre_propietario: nombrePropietario,
    departamento: created.municipalidad?.nombre ?? null,
    direccion: created.proyecto?.direccion ?? null,
    cantidad_visitas: tarifa?.cantidad_visitas ?? 0,
    categoria: tarifa?.categoria ?? "—",
    cip_delegado: cipDelegado,
    uit_valor: uitValor,
    monto_equivalente: montoEquivalente,
    porcentaje_aplicar: porcentajeAplicar,
    costo_por_visita: tarifa?.costo_por_visita ?? 0,
    visitas_minimas: tarifa?.visitas_minimas ?? 0,
    derecho: created.valores.subtotal, // derecho = subtotal for IO
    subtotal: created.valores.subtotal,
    igv: created.valores.igv,
    total: created.valores.total,
    liquidacion_total: created.valores.total,
    total_a_pagar: created.valores.total_a_pagar,
    inspector_cip: inspectorCip,
    inspector_nombre: inspectorNombre,
    tramitado_por: tramitadoPor,
    telefono: telefono,
    hecho_por: hechoPor,
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

export async function printInspeccionObraDocument(data: IOPPrintData) {
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

    const pdfElement = buildIOPdfElement(data, frameDocument);
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

function buildIOPdfElement(data: IOPPrintData, ownerDocument: Document) {
  const {
    public_id,
    fecha_registro,
    municipalidad_codigo,
    ruc,
    razon_social,
    nombre_propietario,
    departamento,
    direccion,
    cantidad_visitas,
    cip_delegado,
    uit_valor,
    monto_equivalente,
    porcentaje_aplicar,
    subtotal,
    igv,
    total,
    liquidacion_total,
    total_a_pagar,
    tramitado_por,
    telefono,
    hecho_por,
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

  // ── Header ──────────────────────────────────────────────────────────────────
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
  appendText(brandText, "p", "COMISION DE DELEGADOS MUNICIPALES", {
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
  appendText(notice, "p", "IMPORTANTE ESTA LIQUIDACION Y SU", {
    margin: "0",
    fontWeight: "700",
    borderBottom: "1px solid #111827",
  });
  appendText(notice, "p", "COMPROBANTE DE PAGO ADJUNTARLA AL EXPEDIENTE", {
    margin: "4px 0 0",
    fontWeight: "700",
    borderBottom: "1px solid #111827",
    fontSize: "11px",
  });
  appendText(notice, "p", "CTA 462021", {
    margin: "6px 0 0",
    fontSize: "20px",
    fontWeight: "700",
    letterSpacing: "0.12em",
  });
  appendText(notice, "p", `Codigo de Pago ${municipalidad_codigo || "L7"}`, {
    margin: "2px 0 0",
    fontSize: "11px",
  });
  appendText(notice, "p", `Nro: ${public_id}`, {
    margin: "10px 0 0",
    fontSize: "15px",
    letterSpacing: "0.08em",
    overflowWrap: "anywhere",
  });

  // ── Title ──────────────────────────────────────────────────────────────────
  appendText(
    paper,
    "h2",
    "LIQUIDACION DE DERECHOS POR SUPERVISION DE OBRA DE INGENIERIA",
    {
      margin: "12px 0 8px",
      fontFamily: "Arial, Helvetica, sans-serif",
      fontSize: "18px",
      fontWeight: "900",
      letterSpacing: "-0.03em",
    },
  );

  // ── Body labels ─────────────────────────────────────────────────────────────
  const details = append(paper, "div", {
    display: "grid",
    gridTemplateColumns: "245px 1fr",
    gap: "3px 12px",
    fontSize: "12px",
    lineHeight: "1.25",
  });
  appendReceiptRow(details, "RUC", ruc || "—");
  appendReceiptRow(details, "RAZON SOCIAL", razon_social || "—");
  appendReceiptRow(details, "NOMBRE DEL PROPIETARIO", nombre_propietario || "—");
  appendReceiptRow(details, "DPTO. / PROV. / DISTRITO", departamento || "—");
  appendReceiptRow(details, "DIRECCION DE LA OBRA", direccion || "—");
  if (cantidad_visitas > 0) {
    appendReceiptRow(details, "NUMERO DE SUPERVISIONES", `${cantidad_visitas}`);
  }
  if (cip_delegado) {
    appendReceiptRow(details, "CIP Y NOMBRE DEL DELEGADO SUPERVISOR", cip_delegado);
  }

  // ── Middle: UIT info (left) + Right totals (right) ─────────────────────────
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

  // Left: UIT-related fields (labels only when values unavailable)
  const calc = append(middle, "div", { fontSize: "12px", lineHeight: "1.7" });
  appendReceiptRow(calc, "VALOR VIGENTE DE LA UIT S/.", uit_valor || "—");
  appendReceiptRow(calc, "Monto equivalente a 1 supervision S/.", monto_equivalente || "—");
  appendReceiptRow(calc, "% A APLICAR SOBRE LA UIT", porcentaje_aplicar || "—");

  // Right: Totals block
  const totals = append(middle, "div", { fontSize: "12px", lineHeight: "1.55" });
  appendTotalLine(totals, "SUBTOTAL S/.", formatCurrency(subtotal).replace("S/ ", ""));
  appendTotalLine(totals, "I.G.V. S/.", formatCurrency(igv).replace("S/ ", ""));
  // Bordered box around the grand total line
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

  // ── Big center TOTAL A PAGAR ────────────────────────────────────────────────
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

  // ── Footer ──────────────────────────────────────────────────────────────────
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
  appendText(left, "p", "Tel: 202-5066", { margin: "0", fontSize: "10px" });
  appendText(left, "p", `Tramitado por ${tramitado_por || '—'}`, { margin: "8px 0 0" });
  appendText(left, "p", `TELEFONO      ${telefono || '—'}`, { margin: "10px 0 0" });
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
  appendText(right, "p", `Hecho por ${hecho_por || '—'}`, { margin: "0" });
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
