/**
 * pdfTheme — Tema del recibo oficial (fuente de verdad de estilos).
 * Todas las secciones del PDF usan estas constantes, no hardcodean estilos.
 */

export const pdfTheme = {
  /** Fuente principal del recibo (Courier New monospace) */
  fontFamily: "'Courier New', Courier, monospace",
  /** Fuente para títulos institucionales (Arial) */
  fontFamilyDisplay: "Arial, Helvetica, sans-serif",

  colors: {
    ink: "#111827", // texto principal
    muted: "#4b5563", // texto secundario
    light: "#6b7280", // texto terciario
    paper: "#FFFFFF",
  },

  // ── Root ──
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

  // ── Paper (borde del recibo) ──
  paper: {
    border: "2px solid #111827",
    borderRadius: "14px",
    padding: "12px 16px",
    minHeight: "455px",
    boxSizing: "border-box",
  } as Partial<CSSStyleDeclaration>,

  // ── Header grid ──
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
  } as Partial<CSSStyleDeclaration>,

  details: {
    display: "flex",
    flexDirection: "column",
    gap: "1px",
    fontSize: "19px",
    lineHeight: "1.45",
  } as Partial<CSSStyleDeclaration>,

  lowerBody: {
    display: "grid",
    gridTemplateColumns: "minmax(0, 1fr) 240px",
    columnGap: "22px",
    alignItems: "start",
    marginTop: "14px",
  } as Partial<CSSStyleDeclaration>,

  specificFields: {
    display: "flex",
    flexDirection: "column",
    gap: "3px",
    fontSize: "20px",
    lineHeight: "1.5",
  } as Partial<CSSStyleDeclaration>,

  totals: {
    display: "flex",
    flexDirection: "column",
    gap: "2px",
    fontSize: "20px",
    lineHeight: "1.5",
    paddingTop: "0",
  } as Partial<CSSStyleDeclaration>,

  totalBox: {
    display: "flex",
    gap: "8px",
    border: "1px solid #111827",
    borderRadius: "8px",
    padding: "5px 10px",
    marginTop: "4px",
  } as Partial<CSSStyleDeclaration>,

  pay: {
    display: "grid",
    gridTemplateColumns: "1fr auto 1fr",
    alignItems: "center",
    gap: "16px",
    marginTop: "16px",
  } as Partial<CSSStyleDeclaration>,

  totalPagar: {
    textAlign: "center",
    fontSize: "28px",
    fontWeight: "700",
    letterSpacing: "0.06em",
  } as Partial<CSSStyleDeclaration>,

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

  noComprobante: {
    whiteSpace: "pre-line",
    textAlign: "center",
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "19px",
    fontWeight: "900",
    lineHeight: "1.05",
  } as Partial<CSSStyleDeclaration>,
} as const;

export type PdfTheme = typeof pdfTheme;
