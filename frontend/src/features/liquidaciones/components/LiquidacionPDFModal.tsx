"use client";

import { useRef, useCallback, useState } from "react";
import Image from "next/image";
import { FileDown, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GenericModal } from "@/components/genericModal/GenericModal";
import type { LiquidacionCardBase } from "../types/liquidacion-general";
import { kindLabel, formatCurrency, formatDate } from "./LiquidacionGeneralCard";

const PDF_CSS = `
  .pdf-primary { color: #6B1D2F !important; }
  .pdf-primary-bg { background-color: #6B1D2F !important; }
  .pdf-primary-bg-10 { background-color: rgba(107, 29, 47, 0.1) !important; }
  .pdf-primary-bg-04 { background-color: rgba(107, 29, 47, 0.04) !important; }
  .pdf-primary-border-20 { border-color: rgba(107, 29, 47, 0.2) !important; }
  .pdf-primary-border-10 { border-color: rgba(107, 29, 47, 0.1) !important; }
  .pdf-muted { color: #6B7280 !important; }
  .pdf-foreground { color: #1F2937 !important; }
  .pdf-destructive { color: rgba(185, 28, 28, 0.7) !important; }
  .pdf-border { border-color: #E5E7EB !important; }
`;

interface LiquidacionPDFModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  item: LiquidacionCardBase;
}

export function LiquidacionPDFModal({ open, onOpenChange, item }: LiquidacionPDFModalProps) {
  const { public_id, estado, fecha_registro, proyecto, municipalidad, valores, delegados, revisiones, tipo_liquidacion, expediente } = item;
  const previewRef = useRef<HTMLDivElement>(null);
  const [generando, setGenerando] = useState(false);

  const handleDescargarPDF = useCallback(async () => {
    if (!previewRef.current) return;
    setGenerando(true);
    try {
      const [html2canvasMod, jsPDFMod] = await Promise.all([
        import("html2canvas"),
        import("jspdf"),
      ]);
      const html2canvas = html2canvasMod.default;
      const jsPDF = jsPDFMod.default;

      const frame = document.createElement("iframe");
      applyStyles(frame, {
        position: "absolute",
        left: "-10000px",
        top: "0",
        width: "794px",
        height: "1123px",
        border: "0",
      });
      document.body.appendChild(frame);

      const frameDocument = frame.contentDocument;
      if (!frameDocument) {
        throw new Error("No se pudo crear el documento aislado para el PDF.");
      }

      frameDocument.open();
      frameDocument.write('<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#FFFFFF;"></body></html>');
      frameDocument.close();

      const pdfElement = buildLiquidacionPdfElement(item, frameDocument);
      frameDocument.body.appendChild(pdfElement);

      let canvas: HTMLCanvasElement;
      try {
        await waitForImages(pdfElement);
        canvas = await html2canvas(pdfElement, {
          scale: 2,
          useCORS: true,
          backgroundColor: "#FFFFFF",
          logging: false,
        });
      } finally {
        frame.remove();
      }

      const imgData = canvas.toDataURL("image/jpeg", 0.95);
      const pdf = new jsPDF("p", "mm", "a4");
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = (canvas.height * pdfWidth) / canvas.width;

      let heightLeft = pdfHeight;
      let position = 0;

      pdf.addImage(imgData, "JPEG", 0, position, pdfWidth, pdfHeight);
      heightLeft -= pdf.internal.pageSize.getHeight();

      while (heightLeft > 0) {
        position = -(pdf.internal.pageSize.getHeight() * (pdf.internal.pages.length - 1));
        pdf.addPage();
        pdf.addImage(imgData, "JPEG", 0, position, pdfWidth, pdfHeight);
        heightLeft -= pdf.internal.pageSize.getHeight();
      }

      pdf.save(`${public_id}.pdf`);
    } catch (err) {
      console.error("Error generando PDF:", err);
    } finally {
      setGenerando(false);
    }
  }, [item, public_id]);

  return (
    <GenericModal open={open} onOpenChange={onOpenChange}>
      <GenericModal.Content size="full">
        <GenericModal.Header
          title={`Vista previa — ${item.public_id}`}
          className="bg-primary/[0.03] border-b border-border px-6 py-4 sm:px-8"
        />
        <GenericModal.Body className="bg-muted/10">
          <div
            ref={previewRef}
            className="max-w-3xl mx-auto space-y-6 bg-white p-8 rounded-xl shadow-sm"
            style={{ fontFamily: "Plus Jakarta Sans, sans-serif", width: "100%" }}
          >
            <style>{PDF_CSS}</style>

            {/* HEADER */}
            <div className="flex items-center justify-between pb-5 pdf-primary-border-20" style={{ borderBottomWidth: 2, borderBottomStyle: "solid" }}>
              <div className="flex items-center gap-4">
                <Image src="/images/logo.png" alt="Logo CIP" width={56} height={56} className="h-14 w-14 object-contain" />
                <div>
                  <h1 className="text-lg pdf-primary" style={{ fontWeight: 800, letterSpacing: "-0.02em", lineHeight: 1 }}>Sistema CAM</h1>
                  <p className="pdf-muted" style={{ fontSize: 10, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.15em" }}>Comisión de Asuntos Municipales</p>
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <h2 className="pdf-primary" style={{ fontSize: 16, fontWeight: 800, letterSpacing: "-0.02em", textTransform: "uppercase" }}>Liquidación</h2>
                <p className="pdf-muted" style={{ fontSize: 10, lineHeight: 1.3 }}>
                  {tipo_liquidacion === "edificacion"
                    ? "Derechos por supervisión de obra"
                    : tipo_liquidacion === "inspeccion-obra"
                    ? "Derechos por inspección de obra"
                    : "Derechos por área de liquidación"}
                </p>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="pdf-primary" style={{ fontSize: 10, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.2em" }}>N° {public_id}</span>
            </div>

            <div className="rounded-xl pdf-border" style={{ border: "1px solid", padding: 16 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 32px" }}>
                <Row label="Tipo" value={kindLabel(tipo_liquidacion)} />
                <Row label="Fecha" value={formatDate(fecha_registro)} />
                <Row label="Expediente" value={expediente || "—"} />
                <Row label="N°" value={public_id} />
              </div>
            </div>

            <Section title="Datos del Contribuyente / Propietario">
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 32px" }}>
                <Row label="RUC" value={proyecto?.entidad?.ruc || proyecto?.entidad?.nombre || "—"} />
                <Row label="Razón social" value={proyecto?.entidad?.nombre || "—"} />
                <Row label="Propietario" value={proyecto?.nombre || "—"} />
                <Row label="Dirección" value={proyecto?.direccion || "—"} />
              </div>
            </Section>

            <Section title="Detalles de Revisión">
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {revisiones.map((rev, idx) => {
                  const isM2 = ["habilitacion-urbana", "mecanica-suelos", "impacto-vial", "taludes"].includes(tipo_liquidacion);
                  const isIO = tipo_liquidacion === "inspeccion-obra";
                  const isEdificacion = tipo_liquidacion === "edificacion";
                  return (
                    <div key={rev.id || idx}>
                      <span className="pdf-primary" style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em" }}>Revisión {idx + 1}</span>
                      {rev.especialidades.length > 0 && (
                        <p className="pdf-muted" style={{ fontSize: 11, marginTop: 2 }}>{rev.especialidades.map((e) => e.nombre).join(", ")}</p>
                      )}
                      {rev.tarifa && (
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 32px", marginTop: 8 }}>
                          {isEdificacion && rev.tarifa.porcentaje_liquidacion != null && (
                            <Row label="% Liquidación" value={`${(Number(rev.tarifa.porcentaje_liquidacion) * 100).toFixed(4)} %`} />
                          )}
                          {isEdificacion && rev.tarifa.derecho_minimo != null && (
                            <Row label="Derecho mínimo" value={formatCurrency(rev.tarifa.derecho_minimo)} />
                          )}
                          {isEdificacion && rev.tarifa.derecho_maximo != null && (
                            <Row label="Derecho máximo" value={formatCurrency(rev.tarifa.derecho_maximo)} />
                          )}
                          {isM2 && rev.tarifa.costo_por_m2 != null && (
                            <Row label="Costo (S/ m²)" value={formatCurrency(rev.tarifa.costo_por_m2)} />
                          )}
                          {isM2 && rev.tarifa.derecho_minimo != null && (
                            <Row label="Derecho mínimo" value={formatCurrency(rev.tarifa.derecho_minimo)} />
                          )}
                          {isM2 && rev.tarifa.derecho_maximo != null && (
                            <Row label="Derecho máximo" value={formatCurrency(rev.tarifa.derecho_maximo)} />
                          )}
                          {isIO && rev.tarifa.costo_por_visita != null && (
                            <Row label="Costo por visita" value={formatCurrency(rev.tarifa.costo_por_visita)} />
                          )}
                          {isIO && rev.tarifa.cantidad_visitas != null && (
                            <Row label="Cant. Visitas" value={rev.tarifa.cantidad_visitas} />
                          )}
                          {isIO && rev.tarifa.categoria != null && (
                            <Row label="Categoría" value={rev.tarifa.categoria} />
                          )}
                          {!isEdificacion && !isM2 && !isIO && rev.tarifa.derecho_minimo != null && (
                            <Row label="Derecho mínimo" value={formatCurrency(rev.tarifa.derecho_minimo)} />
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 32px" }}>
                  <Row label="N.° Revisión" value={item.numero_revision} />
                  <Row label="Monto" value={formatCurrency(valores.subtotal)} />
                </div>
              </div>
            </Section>

            <Section title="Resumen de Liquidación">
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                  <span className="pdf-muted">Subtotal</span>
                  <span className="pdf-foreground" style={{ fontWeight: 700 }}>{formatCurrency(valores.subtotal)}</span>
                </div>
                {"igv" in valores && valores.igv != null && (
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                    <span className="pdf-muted">IGV</span>
                    <span className="pdf-foreground" style={{ fontWeight: 700 }}>{formatCurrency(valores.igv)}</span>
                  </div>
                )}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: 12, borderTop: "2px solid rgba(107, 29, 47, 0.2)" }}>
                  <span className="pdf-primary" style={{ fontSize: 13, fontWeight: 800, textTransform: "uppercase" }}>Total a Pagar</span>
                  <span className="pdf-primary" style={{ fontSize: 20, fontWeight: 800 }}>{formatCurrency(valores.total_a_pagar)}</span>
                </div>
              </div>
            </Section>

            <div style={{ textAlign: "center", paddingTop: 16, borderTop: "2px solid rgba(107, 29, 47, 0.1)" }}>
              <p className="pdf-foreground" style={{ fontSize: 11, fontWeight: 600, marginBottom: 4 }}>Municipalidad: {municipalidad?.nombre || "—"}</p>
              <p className="pdf-primary" style={{ fontSize: 9, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.2em" }}>CAM — Comisión de Asuntos Municipales</p>
              <p className="pdf-destructive" style={{ fontSize: 9, fontWeight: 500, marginTop: 8 }}>Este documento no es comprobante de pago</p>
            </div>
          </div>
        </GenericModal.Body>
        <GenericModal.Footer className="px-6 py-4 sm:px-8 bg-muted/30 border-t border-border">
          <div className="flex flex-row justify-end items-center gap-2 sm:gap-3">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} className="h-10 sm:h-11 rounded-xl font-semibold border-border/60 text-muted-foreground">
              Cerrar
            </Button>
            <Button type="button" disabled={generando} onClick={handleDescargarPDF} className="h-10 sm:h-12 rounded-xl sm:rounded-2xl font-bold shadow-lg shadow-primary/25 gap-2">
              {generando ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileDown className="h-4 w-4" />}
              {generando ? "Generando..." : "Descargar PDF"}
            </Button>
          </div>
        </GenericModal.Footer>
      </GenericModal.Content>
    </GenericModal>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl pdf-border overflow-hidden" style={{ border: "1px solid" }}>
      <div className="flex items-center gap-2 px-4 py-2.5 pdf-border pdf-primary-bg-04" style={{ borderBottom: "1px solid" }}>
        <h4 className="pdf-primary" style={{ fontSize: 10, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.15em" }}>{title}</h4>
      </div>
      <div style={{ padding: 16 }}>{children}</div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      <span className="pdf-muted" style={{ fontSize: 10, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.1em" }}>{label}</span>
      <span className="pdf-foreground" style={{ fontSize: 13, fontWeight: 500 }}>{value}</span>
    </div>
  );
}

function buildLiquidacionPdfElement(item: LiquidacionCardBase, ownerDocument: Document) {
  const { public_id, estado, fecha_registro, proyecto, municipalidad, valores, delegados, revisiones, tipo_liquidacion, expediente } = item;
  const root = ownerDocument.createElement("div");

  applyStyles(root, {
    position: "absolute",
    left: "-10000px",
    top: "0",
    width: "794px",
    minHeight: "1123px",
    backgroundColor: "#FFFFFF",
    color: "#1F2937",
    fontFamily: "Arial, Helvetica, sans-serif",
    padding: "32px",
    boxSizing: "border-box",
  });

  const header = append(root, "div", {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    paddingBottom: "20px",
    borderBottom: "2px solid rgba(107, 29, 47, 0.2)",
  });

  const brand = append(header, "div", { display: "flex", alignItems: "center", gap: "16px" });
  const logo = ownerDocument.createElement("img");
  logo.src = new URL("/images/logo.png", window.location.origin).toString();
  logo.alt = "Logo CIP";
  applyStyles(logo, { width: "56px", height: "56px", objectFit: "contain", display: "block" });
  brand.appendChild(logo);
  const brandText = append(brand, "div");
  appendText(brandText, "h1", "Sistema CAM", {
    margin: "0",
    color: "#6B1D2F",
    fontSize: "18px",
    fontWeight: "800",
    letterSpacing: "-0.02em",
    lineHeight: "1",
  });
  appendText(brandText, "p", "Comisión de Asuntos Municipales", mutedLabelStyle({ margin: "6px 0 0" }));

  const subtitleMap: Record<string, string> = {
    edificacion: "Derechos por supervisión de obra",
    "habilitacion-urbana": "Derechos por área de liquidación",
    "mecanica-suelos": "Derechos por área de liquidación",
    "impacto-vial": "Derechos por área de liquidación",
    taludes: "Derechos por área de liquidación",
    "inspeccion-obra": "Derechos por inspección de obra",
  };
  const subtitle = subtitleMap[tipo_liquidacion] ?? "Derechos por supervisión de obra";

  const title = append(header, "div", { textAlign: "right" });
  appendText(title, "h2", "Liquidación", {
    margin: "0",
    color: "#6B1D2F",
    fontSize: "16px",
    fontWeight: "800",
    letterSpacing: "-0.02em",
    textTransform: "uppercase",
  });
  appendText(title, "p", subtitle, { margin: "4px 0 0", color: "#6B7280", fontSize: "10px", lineHeight: "1.3" });

  const codeRow = append(root, "div", {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: "24px",
  });
  appendText(codeRow, "span", `N° ${public_id}`, {
    color: "#6B1D2F",
    fontSize: "10px",
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: "0.2em",
  });

  const summary = append(root, "div", sectionBoxStyle({ marginTop: "24px" }));
  const summaryGrid = append(summary, "div", gridStyle());
  appendPdfRow(summaryGrid, "Tipo", kindLabel(tipo_liquidacion));
  appendPdfRow(summaryGrid, "Fecha", formatDate(fecha_registro));
  appendPdfRow(summaryGrid, "Expediente", expediente || "—");
  appendPdfRow(summaryGrid, "N°", public_id);

  appendPdfSection(root, "Datos del Contribuyente / Propietario", (content) => {
    const grid = append(content, "div", gridStyle());
    appendPdfRow(grid, "RUC", proyecto?.entidad?.ruc || proyecto?.entidad?.nombre || "—");
    appendPdfRow(grid, "Razón social", proyecto?.entidad?.nombre || "—");
    appendPdfRow(grid, "Propietario", proyecto?.nombre || "—");
    appendPdfRow(grid, "Dirección", proyecto?.direccion || "—");
  });

  appendPdfSection(root, "Detalles de Revisión", (content) => {
    const stack = append(content, "div", { display: "flex", flexDirection: "column", gap: "12px" });

    // All revisiones with type-specific tariff fields
    const isM2 = ["habilitacion-urbana", "mecanica-suelos", "impacto-vial", "taludes"].includes(tipo_liquidacion);
    const isIO = tipo_liquidacion === "inspeccion-obra";
    const isEdificacion = tipo_liquidacion === "edificacion";

    revisiones.forEach((rev, idx) => {
      const subheader = append(stack, "div", { display: "flex", flexDirection: "column", gap: "4px" });
      appendText(subheader, "span", `Revisión ${idx + 1}`, {
        margin: "0",
        color: "#6B1D2F",
        fontSize: "10px",
        fontWeight: "700",
        textTransform: "uppercase",
        letterSpacing: "0.1em",
      });

      // Especialidades
      if (rev.especialidades.length > 0) {
        appendText(subheader, "span", rev.especialidades.map((e) => e.nombre).join(", "), {
          margin: "2px 0 0",
          color: "#6B7280",
          fontSize: "11px",
          fontWeight: "400",
        });
      }

      if (rev.tarifa) {
        const t = rev.tarifa;
        const tarifaGrid = append(stack, "div", gridStyle());

        if (isEdificacion) {
          if (t.porcentaje_liquidacion != null) {
            appendPdfRow(tarifaGrid, "% Liquidación", `${(Number(t.porcentaje_liquidacion) * 100).toFixed(4)} %`);
          }
          if (t.derecho_minimo != null) {
            appendPdfRow(tarifaGrid, "Derecho mínimo", formatCurrency(t.derecho_minimo));
          }
          if (t.derecho_maximo != null) {
            appendPdfRow(tarifaGrid, "Derecho máximo", formatCurrency(t.derecho_maximo));
          }
        } else if (isM2) {
          if (t.costo_por_m2 != null) {
            appendPdfRow(tarifaGrid, "Costo (S/ m²)", formatCurrency(t.costo_por_m2));
          }
          if (t.derecho_minimo != null) {
            appendPdfRow(tarifaGrid, "Derecho mínimo", formatCurrency(t.derecho_minimo));
          }
          if (t.derecho_maximo != null) {
            appendPdfRow(tarifaGrid, "Derecho máximo", formatCurrency(t.derecho_maximo));
          }
        } else if (isIO) {
          if (t.costo_por_visita != null) {
            appendPdfRow(tarifaGrid, "Costo por visita", formatCurrency(t.costo_por_visita));
          }
          if (t.cantidad_visitas != null) {
            appendPdfRow(tarifaGrid, "Cant. Visitas", t.cantidad_visitas);
          }
          if (t.categoria != null) {
            appendPdfRow(tarifaGrid, "Categoría", t.categoria);
          }
        }

        // Fallback for generic/unknown types
        if (!isEdificacion && !isM2 && !isIO) {
          if (t.derecho_minimo != null) {
            appendPdfRow(tarifaGrid, "Derecho mínimo", formatCurrency(t.derecho_minimo));
          }
          if (t.derecho_maximo != null) {
            appendPdfRow(tarifaGrid, "Derecho máximo", formatCurrency(t.derecho_maximo));
          }
          if (t.porcentaje_minimo_uit != null) {
            appendPdfRow(tarifaGrid, "% UIT", `${(Number(t.porcentaje_minimo_uit) * 100).toFixed(2)} %`);
          }
        }
      }
    });

    appendPdfRow(stack, "N.° Revisión", item.numero_revision);
    appendPdfRow(stack, "Monto", formatCurrency(valores.subtotal));
  });

  appendPdfSection(root, "Resumen de Liquidación", (content) => {
    const stack = append(content, "div", { display: "flex", flexDirection: "column", gap: "8px" });
    appendAmountRow(stack, "Subtotal", formatCurrency(valores.subtotal));
    if ("igv" in valores && valores.igv != null) {
      appendAmountRow(stack, "IGV", formatCurrency(valores.igv));
    }
    const total = append(stack, "div", {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      paddingTop: "12px",
      borderTop: "2px solid rgba(107, 29, 47, 0.2)",
    });
    appendText(total, "span", "Total a Pagar", { color: "#6B1D2F", fontSize: "13px", fontWeight: "800", textTransform: "uppercase" });
    appendText(total, "span", formatCurrency(valores.total_a_pagar), { color: "#6B1D2F", fontSize: "20px", fontWeight: "800" });
  });

  const footer = append(root, "div", {
    textAlign: "center",
    marginTop: "24px",
    paddingTop: "16px",
    borderTop: "2px solid rgba(107, 29, 47, 0.1)",
  });
  appendText(footer, "p", `Municipalidad: ${municipalidad?.nombre || "—"}`, { margin: "0 0 4px", color: "#1F2937", fontSize: "11px", fontWeight: "600" });
  appendText(footer, "p", "CAM - Comisión de Asuntos Municipales", { margin: "0", color: "#6B1D2F", fontSize: "9px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "0.2em" });
  appendText(footer, "p", "Este documento no es comprobante de pago", { margin: "8px 0 0", color: "rgba(185, 28, 28, 0.7)", fontSize: "9px", fontWeight: "500" });

  return root;
}

function appendPdfSection(parent: HTMLElement, title: string, fill: (content: HTMLElement) => void) {
  const section = append(parent, "div", sectionBoxStyle({ marginTop: "24px", overflow: "hidden" }));
  const heading = append(section, "div", {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "10px 16px",
    backgroundColor: "rgba(107, 29, 47, 0.04)",
    borderBottom: "1px solid #E5E7EB",
  });
  appendText(heading, "h4", title, {
    margin: "0",
    color: "#6B1D2F",
    fontSize: "10px",
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: "0.15em",
  });
  const content = append(section, "div", { padding: "16px" });
  fill(content);
}

function appendPdfRow(parent: HTMLElement, label: string, value: React.ReactNode) {
  const row = append(parent, "div", { display: "flex", flexDirection: "column" });
  appendText(row, "span", label, mutedLabelStyle());
  appendText(row, "span", String(value), { color: "#1F2937", fontSize: "13px", fontWeight: "500", lineHeight: "1.35" });
}

function appendAmountRow(parent: HTMLElement, label: string, value: string) {
  const row = append(parent, "div", { display: "flex", justifyContent: "space-between", fontSize: "13px" });
  appendText(row, "span", label, { color: "#6B7280" });
  appendText(row, "span", value, { color: "#1F2937", fontWeight: "700" });
}

function append<T extends keyof HTMLElementTagNameMap>(parent: HTMLElement, tagName: T, styles?: Partial<CSSStyleDeclaration>) {
  const element = parent.ownerDocument.createElement(tagName);
  if (styles) applyStyles(element, styles);
  parent.appendChild(element);
  return element;
}

function appendText<T extends keyof HTMLElementTagNameMap>(parent: HTMLElement, tagName: T, text: string, styles?: Partial<CSSStyleDeclaration>) {
  const element = append(parent, tagName, styles);
  element.textContent = text;
  return element;
}

function applyStyles(element: HTMLElement, styles: Partial<CSSStyleDeclaration>) {
  Object.assign(element.style, styles);
}

function gridStyle(): Partial<CSSStyleDeclaration> {
  return { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 32px" };
}

function sectionBoxStyle(extra?: Partial<CSSStyleDeclaration>): Partial<CSSStyleDeclaration> {
  return { border: "1px solid #E5E7EB", borderRadius: "12px", ...extra };
}

function mutedLabelStyle(extra?: Partial<CSSStyleDeclaration>): Partial<CSSStyleDeclaration> {
  return {
    color: "#6B7280",
    fontSize: "10px",
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: "0.1em",
    ...extra,
  };
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
