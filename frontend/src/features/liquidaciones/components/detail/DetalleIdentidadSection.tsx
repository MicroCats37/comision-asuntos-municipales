"use client";

import { Hash } from "lucide-react";
import type { LiquidacionGeneralOutput } from "@/features/liquidaciones/schemas/liquidacion-base.schema";
import { cn } from "@/lib/utils";
import { formatDate, getEstadoBadgeClass } from "../liquidacion-ui";
import { DetalleField, DetalleSection } from "./DetalleSection";

interface Props {
  lg: LiquidacionGeneralOutput;
}

export function DetalleIdentidadSection({ lg }: Props) {
  return (
    <DetalleSection title="Identidad" icon={Hash} className="lg:col-span-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2">
        <DetalleField label="Expediente" mono>
          {lg.expediente ?? "-"}
        </DetalleField>
        <DetalleField label="Rev. N" mono>
          {lg.numero_revision ?? "-"}
        </DetalleField>
        <DetalleField label="Fecha">
          {formatDate(lg.fecha_registro)}
        </DetalleField>
        <DetalleField label="Estado">
          <span
            className={cn(
              "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider",
              getEstadoBadgeClass(lg.estado ?? ""),
            )}
          >
            {lg.estado ?? "-"}
          </span>
        </DetalleField>
        {lg.codigo_cta ? (
          <DetalleField label="CTA" mono>
            {lg.codigo_cta}
          </DetalleField>
        ) : null}
        {lg.legacy !== undefined ? (
          <DetalleField label="Origen">
            <span
              className={cn(
                "text-sm font-bold",
                lg.legacy ? "text-warning" : "text-success",
              )}
            >
              {lg.legacy ? "Legacy" : "Actual"}
            </span>
          </DetalleField>
        ) : null}
      </div>
    </DetalleSection>
  );
}
