/**
 * LiquidacionPdfPreview — Recibo oficial de liquidación.
 *
 * Renderiza con DOM puro + estilos INLINE (sin Tailwind, sin React) para
 * funcionar dentro del iframe aislado que crea esta función.
 *
 * Arquitectura:
 * - PARTE BASE COMÚN: `buildLiquidacionPdfDom` renderiza header + título
 *   + campos comunes (RUC, RAZÓN, PROPIETARIO, PROYECTO, DPTO, DIR) +
 *   lower body + SUBTOTAL/IGV/TOTAL + TOTAL A PAGAR + footer.
 * - PARTE ESPECÍFICA: la base delega SIEMPRE en `buildExtraFieldRows`
 *   (módulo por motor: porcentaje / m2 / visitas), que devuelve las filas
 *   `[label, value][]` de la columna izquierda del lower body, justo arriba
 *   del resumen. La base no implementa lógica de tipo propia.
 * - Las filas del bloque común también las decide el módulo por tipo
 *   (`buildCommonFieldRows`), para que ninguna regla por tipo viva en la base.
 *
 * Layout visual (igual al PDF legacy aprobado):
 * - Header: brand (logo circular + textos) | bloque amarillo con ⚠ SOLO aviso | caja CTA blanca con Nro/código de pago/CTA
 * - Título pill gris con bordes laterales negros
 * - Campos comunes en lista vertical con label bold + value
 * - Lower body: 2 columnas (specific fields + resumen con borders)
 * - TOTAL A PAGAR grande centrado con borders top/bottom
 * - Footer bento-grid 3 columnas (tramite + ESTE DOCUMENTO + hecho por)
 */
import { createPdfFrame } from "@/components-app/pdf/pdfShell";
import { printHtmlElement } from "@/components-app/pdf/printDocument";
import {
  buildCommonFieldRows,
  buildExtraFieldRows,
} from "./liquidacionPdfHelpers";
import {
  getPdfTitleByTipo,
  type PdfLiquidacionItem,
  type PdfTipoSlug,
} from "./pdfTypes";

// ── Helpers ──────────────────────────────────────────────────────────────

function formatCurrency(value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return "S/ 0.00";
  return `S/ ${Number(value).toLocaleString("es-PE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const date = d
    .toLocaleDateString("es-PE", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    })
    .toUpperCase();
  const time = d.toLocaleTimeString("es-PE", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  return `${date} ${time}`;
}

// ── Primitivas DOM ───────────────────────────────────────────────────────

function append<T extends keyof HTMLElementTagNameMap>(
  parent: HTMLElement,
  tagName: T,
  styles?: Partial<CSSStyleDeclaration>,
  text?: string,
) {
  const el = parent.ownerDocument.createElement(tagName);
  if (styles) Object.assign(el.style, styles);
  if (text !== undefined) el.textContent = text;
  parent.appendChild(el);
  return el;
}

// ── Builder principal (PARTE BASE COMÚN + slot específico) ─────────────

export function buildLiquidacionPdfDom(
  parent: HTMLElement,
  item: PdfLiquidacionItem,
  tipo: PdfTipoSlug,
) {
  const lg = item.liquidacion_general;
  const proyecto = lg.proyecto;
  const entidad = proyecto.entidad ?? null;

  const contactoNombre =
    (lg.contacto &&
      [lg.contacto.nombres, lg.contacto.apellidos].filter(Boolean).join(" ")) ||
    proyecto.nombre_propietario ||
    entidad?.razon_social ||
    "—";
  const contactoTelefono =
    lg.contacto?.telefono || lg.contacto?.celular || null;
  const contactoDni = lg.contacto?.dni || null;
  const hechoPor = lg.usuario_creador
    ? [lg.usuario_creador.nombres, lg.usuario_creador.apellidos]
        .filter(Boolean)
        .join(" ") ||
      lg.usuario_creador.username ||
      "—"
    : "—";

  const subTotal = lg.sub_total ?? 0;
  const total = lg.total ?? 0;
  const igvMonto = total - subTotal;
  const tieneIgv = total !== subTotal && igvMonto > 0;

  // ── Root container ──
  const root = append(parent, "div", {
    fontFamily: "'Courier New', Courier, monospace",
    color: "#111827",
    backgroundColor: "#FFFFFF",
    width: "780px",
    margin: "0 auto",
    padding: "0",
    fontSize: "15px",
    lineHeight: "1.4",
    boxSizing: "border-box",
  });
  root.setAttribute("data-pdf-host", "true");

  // ── Paper wrapper ──
  const paper = append(root, "div", {
    border: "2px solid #111827",
    borderRadius: "10px",
    padding: "12px 16px",
    boxSizing: "border-box",
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  });

  // ── Header: brand | caja CTA blanca ──
  const header = append(paper, "div", {
    display: "grid",
    gridTemplateColumns: "minmax(0, 1.7fr) minmax(0, 1fr)",
    gap: "12px",
    alignItems: "stretch",
  });

  // ── Brand: logo circular + textos institucionales ──
  // Centrado en las dos ejes: el bloque (logo + textos) queda al centro de
  // la celda del header y los textos se centran contra el logo.
  const brand = append(header, "div", {
    display: "grid",
    gridTemplateColumns: "82px minmax(0, 1fr)",
    gap: "14px",
    alignItems: "center",
    alignContent: "center",
  });
  const doc = parent.ownerDocument;
  const logoBox = append(brand, "div", {
    width: "76px",
    height: "76px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#fef2f2",
    border: "1.5px solid #7c2d12",
    borderRadius: "9999px",
    overflow: "hidden",
  });
  // Logo embebido como <img>. Si falla, mostramos fallback "CIP".
  const logoImg = doc.createElement("img");
  logoImg.src = "/images/logo.png";
  logoImg.alt = "Logo CIP";
  Object.assign(logoImg.style, {
    width: "100%",
    height: "100%",
    objectFit: "contain",
    display: "block",
  });
  logoImg.addEventListener(
    "error",
    () => {
      logoImg.remove();
      const fallback = doc.createElement("div");
      Object.assign(fallback.style, {
        color: "#7c2d12",
        fontWeight: "900",
        fontSize: "26px",
        letterSpacing: "0.05em",
      });
      fallback.textContent = "CIP";
      logoBox.appendChild(fallback);
    },
    { once: true },
  );
  logoBox.appendChild(logoImg);

  const brandText = append(brand, "div", {
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    textAlign: "left",
    lineHeight: "1.2",
  });
  append(
    brandText,
    "h1",
    {
      margin: "0",
      fontSize: "18px",
      fontWeight: "900",
      lineHeight: "1.15",
      letterSpacing: "-0.01em",
      textWrap: "pretty",
    },
    "COLEGIO DE INGENIEROS DEL PERÚ",
  );
  append(
    brandText,
    "p",
    {
      margin: "6px 0 0",
      fontSize: "13px",
      letterSpacing: "0.03em",
      color: "#4b5563",
      textWrap: "pretty",
    },
    "CONSEJO DEPARTAMENTAL DE LIMA",
  );
  append(
    brandText,
    "p",
    {
      margin: "3px 0 0",
      fontSize: "13px",
      letterSpacing: "0.03em",
      color: "#4b5563",
      textWrap: "pretty",
    },
    "COMISIÓN DE ASUNTOS MUNICIPALES",
  );

  // ── Caja CTA blanca ──
  // El Nro ocupa el slot grande y el código CTA el slot chico: intercambian
  // tamaño y lugar respecto al recibo legacy.
  const ctaBox = append(header, "div", {
    border: "2px solid #111827",
    borderRadius: "8px",
    padding: "14px 12px",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    textAlign: "center",
    gap: "4px",
    backgroundColor: "#ffffff",
  });
  append(
    ctaBox,
    "p",
    {
      margin: "0",
      color: "#6b7280",
      fontSize: "13px",
      fontWeight: "700",
      letterSpacing: "0.08em",
      textTransform: "uppercase",
    },
    "Nro",
  );
  append(
    ctaBox,
    "p",
    {
      margin: "2px 0 0",
      color: "#111827",
      fontSize: "32px",
      fontWeight: "900",
      letterSpacing: "0.12em",
      lineHeight: "1",
    },
    item.liquidacion_especifica?.numero != null
      ? `${item.liquidacion_especifica.numero}`
      : "—",
  );
  append(
    ctaBox,
    "p",
    {
      margin: "6px 0 0",
      color: "#6b7280",
      fontSize: "13px",
      fontWeight: "700",
      letterSpacing: "0.04em",
    },
    `Código de Pago: ${lg.municipalidad?.codigo || "—"}`,
  );
  append(
    ctaBox,
    "p",
    {
      margin: "4px 0 0",
      color: "#111827",
      fontSize: "15px",
      fontWeight: "900",
      letterSpacing: "0.08em",
    },
    `CTA: ${lg.codigo_cta ?? "46201"}`,
  );

  // ── Título oficial (pill gris con bordes negros laterales) ──
  append(
    paper,
    "div",
    {
      margin: "10px 0 0",
      padding: "10px 14px",
      fontSize: "20px",
      fontWeight: "900",
      letterSpacing: "0.02em",
      lineHeight: "1.2",
      color: "#111827",
      backgroundColor: "#f3f4f6",
      borderRadius: "4px",
      textAlign: "center",
      textTransform: "uppercase",
      borderLeft: "4px solid #111827",
      borderRight: "4px solid #111827",
    },
    getPdfTitleByTipo(tipo),
  );

  // ── Detalle común (RUC, RAZÓN, PROPIETARIO, PROYECTO, DPTO, DIR) ──
  // Las filas las decide el módulo por tipo (`buildCommonFieldRows`).
  const detailsBox = append(paper, "div", {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    marginTop: "14px",
    fontSize: "18px",
  });
  const labelW = "260px";
  const fieldRow = (label: string, value: string) => {
    const row = append(detailsBox, "div", {
      display: "flex",
      alignItems: "baseline",
      gap: "6px",
    });
    append(
      row,
      "span",
      {
        fontWeight: "900",
        minWidth: labelW,
        flexShrink: "0",
        color: "#111827",
        whiteSpace: "nowrap",
        overflow: "hidden",
        textOverflow: "ellipsis",
        fontSize: "18px",
      },
      label,
    );
    append(
      row,
      "span",
      {
        color: "#374151",
        overflowWrap: "break-word",
        fontWeight: "500",
        fontSize: "18px",
      },
      `: ${value || "—"}`,
    );
  };
  for (const [label, value] of buildCommonFieldRows(item, tipo)) {
    fieldRow(label, value);
  }

  // ── Lower body: específicos (izq) | resumen (der) ──
  const lowerBody = append(paper, "div", {
    display: "grid",
    gridTemplateColumns: "minmax(0, 1fr) 260px",
    columnGap: "24px",
    alignItems: "start",
    marginTop: "12px",
  });

  const specificFields = append(lowerBody, "div", {
    display: "flex",
    flexDirection: "column",
    gap: "5px",
    fontSize: "18px",
  });
  const labelRow = (label: string, value: string) => {
    const row = append(specificFields, "div", {
      display: "flex",
      alignItems: "baseline",
      gap: "6px",
    });
    append(
      row,
      "span",
      {
        fontWeight: "900",
        minWidth: labelW,
        flexShrink: "0",
        color: "#111827",
        whiteSpace: "nowrap",
        overflow: "hidden",
        textOverflow: "ellipsis",
        fontSize: "18px",
      },
      label,
    );
    append(
      row,
      "span",
      {
        color: "#374151",
        overflowWrap: "break-word",
        fontWeight: "500",
        fontSize: "18px",
      },
      `: ${value || "—"}`,
    );
  };

  // PARTE ESPECÍFICA: el bloque por motor se delega SIEMPRE al módulo
  // canónico (`buildExtraFieldRows`). La base no implementa lógica de tipo
  // propia — así ningún call site puede producir un recibo con campos
  // faltantes por olvidar un argumento.
  const rows = buildExtraFieldRows(item, tipo);
  for (const [label, value] of rows) {
    labelRow(label, value);
  }

  // ── Resumen (cajita a la derecha con borders estilo legacy) ──
  const totalsBox = append(lowerBody, "div", {
    display: "flex",
    flexDirection: "column",
    gap: "0",
    fontSize: "18px",
    border: "1.5px solid #111827",
    borderRadius: "4px",
    backgroundColor: "#ffffff",
    overflow: "hidden",
  });
  const totalLine = (label: string, value: string) => {
    const row = append(totalsBox, "div", {
      display: "grid",
      gridTemplateColumns: "1fr auto",
      gap: "12px",
      padding: "6px 10px",
      borderBottom: "1px solid #111827",
      fontWeight: "700",
    });
    append(row, "span", undefined, label);
    append(row, "span", undefined, value);
  };
  totalLine("SUBTOTAL S/.", formatCurrency(subTotal).replace("S/ ", ""));
  if (tieneIgv) {
    totalLine("I.G.V. S/.", formatCurrency(igvMonto).replace("S/ ", ""));
  }
  const totalBox = append(totalsBox, "div", {
    display: "flex",
    gap: "8px",
    padding: "10px 14px",
    fontSize: "20px",
    fontWeight: "900",
    backgroundColor: "#f3f4f6",
  });
  append(totalBox, "span", { flex: "1" }, "TOTAL S/.");
  append(totalBox, "span", undefined, formatCurrency(total).replace("S/ ", ""));

  // ── TOTAL A PAGAR grande (con borders top/bottom) ──
  const pay = append(paper, "div", {
    display: "grid",
    gridTemplateColumns: "1fr auto 1fr",
    alignItems: "center",
    gap: "12px",
    padding: "14px 0",
    marginTop: "16px",
    borderTop: "2px solid #111827",
    borderBottom: "2px solid #111827",
  });
  append(pay, "div");
  append(
    pay,
    "div",
    {
      textAlign: "center",
      fontSize: "32px",
      fontWeight: "900",
      letterSpacing: "0.06em",
    },
    `TOTAL A PAGAR S/. ${formatCurrency(total).replace("S/ ", "")}`,
  );
  append(pay, "div");

  // ── Footer: bento-grid 3 columnas (12px) ──
  const footer = append(paper, "div", {
    display: "grid",
    gridTemplateColumns: "1fr auto 1fr",
    gap: "24px",
    alignItems: "start",
    marginTop: "18px",
    paddingTop: "12px",
    borderTop: "1px solid #e5e7eb",
    fontSize: "12px",
    lineHeight: "1.5",
  });

  // Left
  const left = append(footer, "div", {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
  });
  append(
    left,
    "p",
    { margin: "0", fontWeight: "800" },
    "COMISIÓN DE ASUNTOS MUNICIPALES",
  );
  append(left, "p", { margin: "0" }, "Tel.: 202-5066");
  append(
    left,
    "p",
    { margin: "6px 0 0", fontWeight: "700" },
    `Tramitado por ${contactoNombre}`,
  );
  append(
    left,
    "p",
    { margin: "0", fontWeight: "700" },
    contactoTelefono
      ? `${lg.contacto?.telefono ? "TELÉFONO" : "CELULAR"}: ${contactoTelefono}${
          contactoDni ? `   |   DNI ${contactoDni}` : ""
        }`
      : contactoDni
        ? `DNI: ${contactoDni}`
        : "TELÉFONO      —",
  );

  // Center: sección amarilla fusionada con la instrucción de adjuntar.
  // El aviso va arriba y la instrucción debajo, en tamaño mayor.
  const centerBox = append(footer, "div", {
    whiteSpace: "pre-line",
    textAlign: "center",
    border: "2px solid #b45309",
    backgroundColor: "#fef3c7",
    borderRadius: "8px",
    padding: "12px 16px",
    alignSelf: "stretch",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: "8px",
  });
  append(
    centerBox,
    "p",
    {
      margin: "0",
      fontWeight: "900",
      color: "#7c2d12",
      fontSize: "13px",
      lineHeight: "1.25",
      letterSpacing: "0.02em",
    },
    "⚠ ESTE NO ES UN COMPROBANTE DE PAGO",
  );
  append(
    centerBox,
    "p",
    {
      margin: "0",
      fontWeight: "900",
      color: "#7c2d12",
      fontSize: "15px",
      lineHeight: "1.3",
      letterSpacing: "0.04em",
    },
    "ESTE SE DEBERÁ DE ADJUNTAR\nJUNTO AL COMPROBANTE\nDE PAGO",
  );

  // Right
  const right = append(footer, "div", {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    alignItems: "flex-end",
  });
  append(
    right,
    "p",
    { margin: "0", fontWeight: "700", textAlign: "right" },
    `Hecho por ${hechoPor}`,
  );
  append(
    right,
    "p",
    { margin: "0", textAlign: "right" },
    formatDateTime(lg.fecha_registro),
  );

  return root;
}

// ── Wrapper para imprimir ───────────────────────────────────────────────

export async function printLiquidacionPreview(
  item: PdfLiquidacionItem,
  tipo: PdfTipoSlug,
) {
  const { frame, frameDocument } = createPdfFrame();
  try {
    buildLiquidacionPdfDom(frameDocument.body, item, tipo);
    const pdfElement = frameDocument.querySelector(
      "[data-pdf-host]",
    ) as HTMLElement | null;
    const target = pdfElement ?? frameDocument.body;
    const docId =
      item.liquidacion_general.expediente || item.liquidacion_general.id;
    await printHtmlElement(target, docId);
  } finally {
    frame.remove();
  }
}
