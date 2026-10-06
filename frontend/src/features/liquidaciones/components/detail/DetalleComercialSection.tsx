"use client";

import { Calculator, CheckCircle2, XCircle } from "lucide-react";
import type { LiquidacionGeneralOutput } from "@/features/liquidaciones/schemas/liquidacion-base.schema";
import { cn } from "@/lib/utils";
import { formatCurrency } from "../liquidacion-ui";
import { DetalleField, DetalleSection } from "./DetalleSection";

interface Props {
  lg: LiquidacionGeneralOutput;
}

export function DetalleComercialSection({ lg }: Props) {
  const comprobanteActivo = lg.comprobantes?.find((c) => c.activo) ?? null;
  const tieneComprobante = comprobanteActivo != null;

  return (
    <DetalleSection
      title="Comercial"
      icon={Calculator}
      className="lg:col-span-6"
    >
      <div className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2">
          <DetalleField label="Subtotal" mono>
            {formatCurrency(lg.sub_total)}
          </DetalleField>
          <DetalleField label="Total" mono>
            <span className="text-base font-black text-primary">
              {formatCurrency(lg.total)}
            </span>
          </DetalleField>
          {lg.igv ? (
            <DetalleField label="IGV">
              <span className="font-mono tabular-nums">{lg.igv.valor}%</span>
            </DetalleField>
          ) : null}
          {lg.uit ? (
            <DetalleField label="UIT" mono>
              {formatCurrency(lg.uit.valor)}
            </DetalleField>
          ) : null}
        </div>

        <div className="rounded-lg border border-border/40 bg-muted/20 p-3 flex items-start gap-2.5">
          {tieneComprobante ? (
            <CheckCircle2 className="h-4 w-4 text-success shrink-0 mt-0.5" />
          ) : (
            <XCircle className="h-4 w-4 text-muted-foreground/50 shrink-0 mt-0.5" />
          )}
          <div className="min-w-0">
            <p
              className={cn(
                "text-[10px] font-bold uppercase tracking-wider mb-0.5",
                tieneComprobante ? "text-success" : "text-muted-foreground/70",
              )}
            >
              Comprobante {tieneComprobante ? "activo" : "no asignado"}
            </p>
            {comprobanteActivo ? (
              <div className="flex flex-wrap items-baseline gap-2 text-sm">
                <span className="font-mono font-bold text-foreground">
                  {comprobanteActivo.tipo_comprobante ?? "-"}
                </span>
                <span className="font-mono text-muted-foreground">
                  {comprobanteActivo.serie}-{comprobanteActivo.numero}
                </span>
                {comprobanteActivo.monto != null ? (
                  <span className="font-mono tabular-nums text-foreground/80">
                    {formatCurrency(comprobanteActivo.monto)}
                  </span>
                ) : null}
                {comprobanteActivo.fecha_emision ? (
                  <span className="text-[10px] text-muted-foreground">
                    Emision: {comprobanteActivo.fecha_emision}
                  </span>
                ) : null}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground/60 italic">
                Esta liquidacion aun no tiene comprobante registrado.
              </p>
            )}
          </div>
        </div>
      </div>
    </DetalleSection>
  );
}
