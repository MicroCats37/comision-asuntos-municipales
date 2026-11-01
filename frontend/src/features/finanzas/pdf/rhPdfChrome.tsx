"use client";

/**
 * rhPdfChrome — Piezas de ESTILO visual para los PDFs de RH mensual.
 *
 * No define la DISTRIBUCIÓN de cada documento (esa es propia de cada PDF:
 * Inspector y Delegado mantienen la de sus documentos oficiales originales).
 * Solo aporta el lenguaje visual del PDF de Liquidaciones: tipografía
 * monoespaciada, bordes negros, fondos grises y cajas con el mismo tratamiento.
 *
 * Los estilos son INLINE (como el PDF de Liquidaciones) porque el documento
 * se monta en un iframe aislado donde el CSS de la app no está disponible.
 */
import type { CSSProperties, ReactNode } from "react";

/** Tokens visuales (mismos valores que el PDF de Liquidaciones). */
export const rhPdfStyles = {
  root: {
    fontFamily: "'Courier New', Courier, monospace",
    color: "#111827",
    backgroundColor: "#FFFFFF",
    margin: "0 auto",
    padding: "0",
    lineHeight: "1.4",
    boxSizing: "border-box",
    // Ancho fijo (igual que el PDF de Liquidaciones): al imprimir, el
    // navegador escala el documento a la hoja y queda rectangular.
    width: "780px",
  },
  /** Marco del documento. */
  paper: {
    border: "2px solid #111827",
    borderRadius: "10px",
    padding: "12px 16px",
    display: "flex",
    flexDirection: "column",
    gap: "10px",
    boxSizing: "border-box",
  },
  /** Header: escudo | bloque central | extremo derecho. */
  header: {
    display: "grid",
    gridTemplateColumns: "78px minmax(0, 1fr) 150px",
    gap: "12px",
    alignItems: "start",
  },
  /** Escudo circular institucional. */
  logoBox: {
    width: "76px",
    height: "76px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#fef2f2",
    border: "1.5px solid #7c2d12",
    borderRadius: "9999px",
    overflow: "hidden",
  },
  /** Bloque central: título oficial y subtítulo. */
  titleBlock: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    textAlign: "center",
    lineHeight: "1.2",
  },
  docTitle: {
    margin: "0",
    fontSize: "15px",
    fontWeight: "700",
    letterSpacing: "0.02em",
    lineHeight: "1.25",
    color: "#111827",
    textWrap: "pretty",
  },
  docSubtitle: {
    margin: "3px 0 0",
    fontSize: "11px",
    fontWeight: "600",
    lineHeight: "1.3",
    color: "#1f2937",
    textWrap: "pretty",
  },
  /** Renglón con la persona (inspector/delegado) bajo el título. */
  personLine: {
    margin: "6px 0 0",
    alignSelf: "flex-start",
    fontSize: "10px",
    lineHeight: "1.3",
    color: "#111827",
    textWrap: "pretty",
  },
  /** Extremo derecho del header (periodo). */
  sideBox: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "flex-end",
    alignItems: "flex-end",
    gap: "4px",
    paddingTop: "2px",
  },
  sideValue: {
    margin: "0",
    fontSize: "11px",
    fontWeight: "700",
    letterSpacing: "0.06em",
    textAlign: "right",
    color: "#111827",
    textWrap: "pretty",
  },
  sideValueUnderlined: {
    margin: "0",
    fontSize: "11px",
    fontWeight: "700",
    textAlign: "right",
    textDecoration: "underline",
    color: "#111827",
  },
  /** Fecha de creación del documento (esquina superior derecha). */
  createdAt: {
    margin: "0",
    fontSize: "9px",
    fontWeight: "700",
    letterSpacing: "0.04em",
    textAlign: "right",
    color: "#111827",
    whiteSpace: "nowrap",
  },
  /** Renglones label + valor (municipalidad, delegado). */
  labelLine: {
    display: "flex",
    alignItems: "baseline",
    gap: "10px",
    fontSize: "11px",
    lineHeight: "1.35",
    color: "#111827",
  },
  labelLineLabel: {
    fontWeight: "700",
    letterSpacing: "0.04em",
  },
  labelLineValue: {
    fontWeight: "700",
    textWrap: "pretty",
  },
  /** Tabla clásica: bordes negros, texto que envuelve. */
  table: {
    width: "100%",
    borderCollapse: "collapse",
    tableLayout: "fixed",
    fontSize: "9px",
    lineHeight: "1.25",
  },
  th: {
    border: "1px solid #000000",
    padding: "3px 1px",
    fontSize: "7.5px",
    fontWeight: "700",
    textAlign: "center",
    textTransform: "uppercase",
    letterSpacing: "0.01em",
    verticalAlign: "middle",
    textWrap: "balance",
    overflowWrap: "break-word",
  },
  td: {
    border: "1px solid #000000",
    padding: "2px 1px",
    fontSize: "8.5px",
    textAlign: "left",
    verticalAlign: "middle",
    textWrap: "pretty",
    overflowWrap: "break-word",
  },
  tdRight: {
    border: "1px solid #000000",
    padding: "2px 1px",
    fontSize: "8.5px",
    textAlign: "right",
    verticalAlign: "middle",
    whiteSpace: "nowrap",
  },
  tdCenter: {
    border: "1px solid #000000",
    padding: "2px 1px",
    fontSize: "8.5px",
    textAlign: "center",
    verticalAlign: "middle",
    whiteSpace: "nowrap",
  },
  /** Caja de totales alineada a la derecha (SUB TOTAL / DESCUENTOS / …). */
  totalsBox: {
    marginLeft: "auto",
    marginTop: "6px",
    width: "230px",
    borderCollapse: "collapse",
    fontSize: "9.5px",
  },
  totalsRow: {
    border: "1px solid #000000",
    padding: "3px 6px",
    fontWeight: "700",
    color: "#111827",
  },
  totalsLabel: {
    textAlign: "left",
  },
  totalsValue: {
    textAlign: "right",
  },
  /** Fila de total destacado (fondo gris, como el PDF de Liquidaciones). */
  totalsTotalRow: {
    border: "1px solid #000000",
    padding: "3px 6px",
    fontWeight: "700",
    color: "#111827",
    backgroundColor: "#f3f4f6",
  },
  /** Importe final destacado (como el PDF de Liquidaciones). */
  amountBox: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "12px",
    marginLeft: "auto",
    marginTop: "6px",
    width: "290px",
    border: "2px solid #111827",
    borderRadius: "8px",
    padding: "8px 14px",
    backgroundColor: "#ffffff",
  },
  amountLabel: {
    margin: "0",
    fontSize: "13px",
    fontWeight: "900",
    letterSpacing: "0.04em",
    color: "#111827",
  },
  amountValue: {
    margin: "0",
    fontSize: "15px",
    fontWeight: "900",
    color: "#111827",
  },
} satisfies Record<string, CSSProperties>;

/**
 * Fecha de creación del documento, en el formato del documento oficial:
 * `06/05/2026 06:51:20 PM`.
 */
export function formatCreatedAt(iso?: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("es-PE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });
}

/** Marco del documento. */
export function RhPdfPaper({ children }: { children: ReactNode }) {
  return (
    <div style={rhPdfStyles.root} data-pdf-host="true">
      <div style={rhPdfStyles.paper}>{children}</div>
    </div>
  );
}

/** Escudo circular institucional. */
export function RhPdfLogo() {
  return (
    <div style={rhPdfStyles.logoBox}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/images/logo.png"
        alt="Logo CIP"
        style={{
          width: "100%",
          height: "100%",
          objectFit: "contain",
          display: "block",
        }}
      />
    </div>
  );
}

/**
 * Renglón label + valor (municipalidad, delegado).
 * El rótulo va en negrita y el valor a la derecha, como en el documento.
 */
export function RhPdfLabelLine({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div style={rhPdfStyles.labelLine}>
      <span style={rhPdfStyles.labelLineLabel}>{label}</span>
      <span style={rhPdfStyles.labelLineValue}>{value}</span>
    </div>
  );
}
