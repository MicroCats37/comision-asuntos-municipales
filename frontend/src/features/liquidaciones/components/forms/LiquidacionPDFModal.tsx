"use client";

import { FileDown, Loader2, Printer } from "lucide-react";
/**
 * LiquidacionPDFModal — Modal base para ver/descargar/imprimir el PDF de una liquidación.
 *
 * Recibe el item (del backend) + tipo. Usa buildLiquidacionPdfElement (base común + motor)
 * y los helpers genéricos de components-app/pdf (printDocument + downloadPdf).
 */
import { useCallback, useState } from "react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Button } from "@/components/ui/button";
import { downloadHtmlAsPdf } from "@/components-app/pdf/downloadPdf";
import { createPdfFrame } from "@/components-app/pdf/pdfShell";
import { printHtmlElement } from "@/components-app/pdf/printDocument";
import {
  buildLiquidacionPdfElement,
  type PdfLiquidacionItem,
} from "../../pdf/buildLiquidacionPdfElement";

interface LiquidacionPDFModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  item: PdfLiquidacionItem;
  tipo: string;
}

export function LiquidacionPDFModal({
  open,
  onOpenChange,
  item,
  tipo,
}: LiquidacionPDFModalProps) {
  const [generando, setGenerando] = useState(false);
  const [imprimiendo, setImprimiendo] = useState(false);

  const lg = item.liquidacion_general;
  const docId = lg.expediente || lg.id;

  const handleDescargarPDF = useCallback(async () => {
    setGenerando(true);
    try {
      // Construir en frame aislado y descargar
      const { frame, frameDocument } = createPdfFrame();
      try {
        const pdfElement = buildLiquidacionPdfElement(
          item,
          tipo,
          frameDocument,
        );
        await downloadHtmlAsPdf(pdfElement, `${docId}.pdf`);
      } finally {
        frame.remove();
      }
    } catch (err) {
      console.error("Error generando PDF:", err);
    } finally {
      setGenerando(false);
    }
  }, [item, tipo, docId]);

  const handleImprimir = useCallback(async () => {
    setImprimiendo(true);
    try {
      const { frame, frameDocument } = createPdfFrame();
      try {
        const pdfElement = buildLiquidacionPdfElement(
          item,
          tipo,
          frameDocument,
        );
        await printHtmlElement(pdfElement, docId);
      } finally {
        frame.remove();
      }
    } catch (err) {
      console.error("Error imprimiendo liquidación:", err);
    } finally {
      setImprimiendo(false);
    }
  }, [item, tipo, docId]);

  return (
    <GenericModal open={open} onOpenChange={onOpenChange}>
      <GenericModal.Content size="full">
        <GenericModal.Header
          title={`Liquidación creada — ${docId}`}
          className="bg-primary/[0.03] border-b border-border px-6 py-4 sm:px-8"
        />
        <GenericModal.Body className="bg-muted/10 px-6 py-6 sm:px-8">
          <div className="mx-auto max-w-xl rounded-xl border border-border bg-card p-5 shadow-sm space-y-3">
            <div>
              <p className="text-sm font-semibold text-foreground">
                Documento listo para imprimir o descargar.
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                La impresión abrirá la ventana nativa del navegador con el
                formato oficial.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-xs text-muted-foreground">N°</span>
                <p className="font-semibold text-foreground">{docId}</p>
              </div>
              <div>
                <span className="text-xs text-muted-foreground">Proyecto</span>
                <p className="font-semibold text-foreground truncate">
                  {lg.proyecto.denominacion}
                </p>
              </div>
              <div>
                <span className="text-xs text-muted-foreground">Revisión</span>
                <p className="font-semibold text-foreground">
                  N° {lg.numero_revision ?? "—"}
                </p>
              </div>
              <div>
                <span className="text-xs text-muted-foreground">
                  Registrado por
                </span>
                <p className="font-semibold text-foreground truncate">
                  {lg.usuario_creador
                    ? [lg.usuario_creador.nombres, lg.usuario_creador.apellidos]
                        .filter(Boolean)
                        .join(" ") ||
                      lg.usuario_creador.username ||
                      "—"
                    : "—"}
                </p>
              </div>
            </div>
          </div>
        </GenericModal.Body>
        <GenericModal.Footer className="px-6 py-4 sm:px-8 bg-muted/30 border-t border-border">
          <div className="flex flex-row justify-end items-center gap-2 sm:gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              className="h-10 sm:h-11 rounded-xl font-semibold border-border/60 text-muted-foreground"
            >
              Cerrar
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={imprimiendo || generando}
              onClick={handleImprimir}
              className="h-10 sm:h-12 rounded-xl sm:rounded-2xl font-bold gap-2"
            >
              {imprimiendo ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Printer className="h-4 w-4" />
              )}
              {imprimiendo ? "Preparando..." : "Imprimir"}
            </Button>
            <Button
              type="button"
              disabled={generando}
              onClick={handleDescargarPDF}
              className="h-10 sm:h-12 rounded-xl sm:rounded-2xl font-bold shadow-lg shadow-primary/25 gap-2"
            >
              {generando ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FileDown className="h-4 w-4" />
              )}
              {generando ? "Generando..." : "Descargar PDF"}
            </Button>
          </div>
        </GenericModal.Footer>
      </GenericModal.Content>
    </GenericModal>
  );
}
