"use client";

import { useCallback, useState } from "react";
import { FileDown, Loader2, Printer } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GenericModal } from "@/components/genericModal/GenericModal";
import type { LiquidacionCardBase } from "../types/liquidacion-general";
import { kindLabel, formatCurrency, formatDate } from "./LiquidacionGeneralCard";

interface LiquidacionPDFModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  item: LiquidacionCardBase;
}

export function LiquidacionPDFModal({ open, onOpenChange, item }: LiquidacionPDFModalProps) {
  const { public_id } = item;
  const [generando, setGenerando] = useState(false);
  const [imprimiendo, setImprimiendo] = useState(false);

  const handleDescargarPDF = useCallback(async () => {
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
        width: "980px",
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
      const pdf = new jsPDF("l", "mm", "a4");
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

  const handleImprimir = useCallback(async () => {
    setImprimiendo(true);
    try {
      await printLiquidacionDocument(item);
    } catch (err) {
      console.error("Error imprimiendo liquidación:", err);
    } finally {
      setImprimiendo(false);
    }
  }, [item]);

  return (
    <GenericModal open={open} onOpenChange={onOpenChange}>
      <GenericModal.Content size="full">
        <GenericModal.Header
          title={`Liquidación creada — ${item.public_id}`}
          className="bg-primary/[0.03] border-b border-border px-6 py-4 sm:px-8"
        />
        <GenericModal.Body className="bg-muted/10 px-6 py-6 sm:px-8">
          <div className="mx-auto max-w-xl rounded-xl border border-border bg-card p-5 shadow-sm space-y-3">
            <div>
              <p className="text-sm font-semibold text-foreground">
                Documento listo para imprimir o descargar.
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                La impresión abrirá la ventana nativa del navegador con el formato oficial.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-xs text-muted-foreground">N°</span>
                <p className="font-semibold text-foreground">{item.public_id}</p>
              </div>
              <div>
                <span className="text-xs text-muted-foreground">Total</span>
                <p className="font-semibold text-primary">{formatCurrency(item.valores.total_a_pagar)}</p>
              </div>
            </div>
          </div>
        </GenericModal.Body>
        <GenericModal.Footer className="px-6 py-4 sm:px-8 bg-muted/30 border-t border-border">
          <div className="flex flex-row justify-end items-center gap-2 sm:gap-3">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} className="h-10 sm:h-11 rounded-xl font-semibold border-border/60 text-muted-foreground">
              Cerrar
            </Button>
            <Button type="button" variant="outline" disabled={imprimiendo || generando} onClick={handleImprimir} className="h-10 sm:h-12 rounded-xl sm:rounded-2xl font-bold gap-2">
              {imprimiendo ? <Loader2 className="h-4 w-4 animate-spin" /> : <Printer className="h-4 w-4" />}
              {imprimiendo ? "Preparando..." : "Imprimir"}
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

export async function printLiquidacionDocument(item: LiquidacionCardBase) {
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
    frameDocument.write(`<!doctype html><html><head><meta charset="utf-8"><title>${item.public_id}</title></head><body style="margin:0;background:#FFFFFF;"></body></html>`);
    frameDocument.close();

    const pdfElement = buildLiquidacionPdfElement(item, frameDocument);
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

function buildLiquidacionPdfElement(item: LiquidacionCardBase, ownerDocument: Document) {
  const { public_id, fecha_registro, proyecto, municipalidad, valores, revisiones, tipo_liquidacion, expediente } = item;
  const root = ownerDocument.createElement("div");
  const firstRevision = revisiones[0];
  const firstTarifa = firstRevision?.tarifa;
  const porcentajeLiquidacion = firstTarifa?.porcentaje_liquidacion != null
    ? `${(Number(firstTarifa.porcentaje_liquidacion) * 100).toFixed(2)}%`
    : "—";
  const date = new Date(fecha_registro);
  const printedDate = Number.isNaN(date.getTime())
    ? formatDate(fecha_registro).toUpperCase()
    : date.toLocaleDateString("es-PE", { day: "2-digit", month: "long", year: "numeric" }).toUpperCase();

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

  const header = append(paper, "div", {
    display: "grid",
    gridTemplateColumns: "minmax(0, 1fr) 330px",
    gap: "18px",
    alignItems: "start",
  });

  const brand = append(header, "div", { display: "grid", gridTemplateColumns: "78px 1fr", gap: "14px", alignItems: "center" });

  const logo = ownerDocument.createElement("img");
  logo.src = new URL("/images/logo.png", window.location.origin).toString();
  logo.alt = "Logo CIP";
  applyStyles(logo, { width: "70px", height: "70px", objectFit: "contain", display: "block" });
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
  appendText(brandText, "p", "CONSEJO DEPARTAMENTAL DE LIMA", { margin: "4px 0 0", fontFamily: "Arial, Helvetica, sans-serif", fontSize: "16px", letterSpacing: "0.04em" });
  appendText(brandText, "p", "COMISION DE ASUNTOS MUNICIPALES", { margin: "2px 0 0", fontFamily: "Arial, Helvetica, sans-serif", fontSize: "16px", letterSpacing: "0.04em" });

  const notice = append(header, "div", { textAlign: "center", fontSize: "12px", lineHeight: "1.35" });
  appendText(notice, "p", "IMPORTANTE: ESTA LIQUIDACION DEBERA", { margin: "0", fontWeight: "700", borderBottom: "1px solid #111827" });
  appendText(notice, "p", "ADJUNTARLA AL COMPROBANTE DE PAGO", { margin: "8px 0 0", fontWeight: "700", borderBottom: "1px solid #111827" });
  appendText(notice, "p", "CTA 46201", { margin: "6px 0 0", fontSize: "20px", fontWeight: "700", letterSpacing: "0.12em" });
  appendText(notice, "p", `Codigo de Pago ${municipalidad?.codigo || "—"}`, { margin: "2px 0 0", fontSize: "11px" });
  appendText(notice, "p", `Nro: ${public_id}`, { margin: "10px 0 0", fontSize: "15px", letterSpacing: "0.08em", overflowWrap: "anywhere" });

  appendText(paper, "h2", "LIQUIDACION DE DERECHOS POR CALIFICACION DE PROYECTOS DE INGENIERIA", {
    margin: "12px 0 8px",
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "18px",
    fontWeight: "900",
    letterSpacing: "-0.03em",
  });

  const details = append(paper, "div", { display: "grid", gridTemplateColumns: "245px 1fr", gap: "3px 12px", fontSize: "12px", lineHeight: "1.25" });
  appendReceiptRow(details, "RUC", proyecto?.entidad?.ruc || "—");
  appendReceiptRow(details, "RAZON SOCIAL", proyecto?.entidad?.nombre || "—");
  appendReceiptRow(details, "NOMBRE DEL PROPIETARIO", proyecto?.entidad?.nombre || proyecto?.nombre || "—");
  appendReceiptRow(details, "NOMBRE DEL PROYECTO", proyecto?.nombre || kindLabel(tipo_liquidacion));
  appendReceiptRow(details, "DPTO. / PROV./ DISTRITO", municipalidad?.nombre || "—");
  appendReceiptRow(details, "DIRECCION DE LA OBRA", proyecto?.direccion || "—");
  appendReceiptRow(details, "VALOR DE LA OBRA DECLARADO S/.", formatCurrency(proyecto?.valor_proyecto ?? valores.subtotal).replace("S/ ", ""));

  const middle = append(paper, "div", { display: "grid", gridTemplateColumns: "1fr 260px", gap: "22px", marginTop: "18px", alignItems: "start" });
  const calc = append(middle, "div", { fontSize: "12px", lineHeight: "1.5" });
  appendText(calc, "p", `PORCENTAJE A APLICAR SOBRE DEL VALOR DE LA OBRA ${porcentajeLiquidacion}`, { margin: "0", fontWeight: "700", maxWidth: "620px" });
  const derechoMinimo = firstTarifa?.derecho_minimo != null ? formatCurrency(firstTarifa.derecho_minimo) : "—";
  appendText(calc, "p", `Derecho minimo ${derechoMinimo} + IGV ***`, { margin: "4px 0 0" });

  const totals = append(middle, "div", { fontSize: "12px", lineHeight: "1.55" });
  appendTotalLine(totals, "SUBTOTAL S/.", formatCurrency(valores.subtotal).replace("S/ ", ""));
  appendTotalLine(totals, "I.G.V. S/.", "igv" in valores ? formatCurrency(valores.igv).replace("S/ ", "") : "—");
  const totalBox = append(totals, "div", { display: "grid", gridTemplateColumns: "1fr auto", gap: "12px", border: "1px solid #111827", borderRadius: "10px", padding: "2px 6px", marginTop: "4px" });
  appendText(totalBox, "span", "TOTAL S/.", { fontWeight: "700" });
  appendText(totalBox, "span", formatCurrency(valores.total_a_pagar).replace("S/ ", ""));

  const pay = append(paper, "div", { display: "grid", gridTemplateColumns: "1fr auto 1fr", alignItems: "center", gap: "16px", marginTop: "18px" });
  append(pay, "div");
  appendText(pay, "div", `TOTAL A PAGAR S/. ${formatCurrency(valores.total_a_pagar).replace("S/ ", "")}`, { textAlign: "center", fontSize: "24px", fontWeight: "700", letterSpacing: "0.08em" });
  append(pay, "div");

  const footer = append(paper, "div", { display: "grid", gridTemplateColumns: "270px 1fr 210px", gap: "16px", alignItems: "end", marginTop: "16px", fontSize: "12px" });
  const left = append(footer, "div", { lineHeight: "1.35" });
  appendText(left, "p", "COMISION DE ASUNTOS MUNICIPALES", { margin: "0", fontSize: "10px", fontWeight: "700" });
  appendText(left, "p", "Tel.: 202-5066", { margin: "0", fontSize: "10px" });
  appendText(left, "p", "Tramitado por —", { margin: "8px 0 0" });
  appendText(left, "p", "TELEFONO      —", { margin: "10px 0 0" });
  appendText(left, "p", printedDate, { margin: "16px 0 0", letterSpacing: "0.08em" });

  appendText(footer, "div", "ESTE DOCUMENTO NO ES\nCOMPROBANTE DE PAGO", {
    whiteSpace: "pre-line",
    textAlign: "center",
    fontFamily: "Arial, Helvetica, sans-serif",
    fontSize: "19px",
    fontWeight: "900",
    lineHeight: "1.05",
  });

  const right = append(footer, "div", { lineHeight: "1.45" });
  appendText(right, "p", "Hecho por —", { margin: "0" });
  appendText(right, "p", new Date().toLocaleTimeString("es-PE", { hour12: false }), { margin: "12px 0 0" });

  return root;
}

function appendReceiptRow(parent: HTMLElement, label: string, value: string) {
  appendText(parent, "span", label, { fontWeight: "700" });
  appendText(parent, "span", `: ${value}`, { overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" });
}

function appendTotalLine(parent: HTMLElement, label: string, value: string) {
  const row = append(parent, "div", { display: "grid", gridTemplateColumns: "1fr auto", gap: "12px" });
  appendText(row, "span", label, { fontWeight: "700" });
  appendText(row, "span", value);
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
