"use client";

import { Maximize2 } from "lucide-react";
import type { M2DatosOut } from "../../schemas/liquidacion-m2.schema";
import { formatCurrency } from "../liquidacion-ui";
import { DetalleField, DetalleSection } from "./DetalleSection";

interface Props {
  m2: M2DatosOut;
}

/**
 * Tipo-specific section for HU / MS — área + tarifa por m² + derechos.
 * Mirrors `DetalleTarifasSection` shape but uses M2DatosOut fields.
 */
export function DetalleAreaTarifaSection({ m2 }: Props) {
  return (
    <DetalleSection
      title="Área y tarifa"
      icon={Maximize2}
      className="lg:col-span-12"
    >
      <div className="px-4 py-3 flex flex-col gap-3">
        <div className="flex flex-wrap gap-x-5 gap-y-2">
          <DetalleField label="Área" mono>
            <span className="text-base font-black text-primary tabular-nums leading-tight">
              {m2.area_m2.toLocaleString("es-PE")}
            </span>
            <span className="text-[10px] font-semibold text-muted-foreground/70 uppercase">
              m²
            </span>
          </DetalleField>
          <DetalleField label="Costo / m²" mono>
            <span className="text-sm font-bold text-primary tabular-nums">
              {m2.costo_por_m2 != null
                ? `S/ ${m2.costo_por_m2.toLocaleString("es-PE", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 4,
                  })}`
                : "—"}
            </span>
          </DetalleField>
          {m2.derecho_minimo != null ? (
            <DetalleField label="Der. Mín." mono>
              {formatCurrency(m2.derecho_minimo)}
            </DetalleField>
          ) : null}
          {m2.derecho_maximo != null ? (
            <DetalleField label="Der. Máx." mono>
              {formatCurrency(m2.derecho_maximo)}
            </DetalleField>
          ) : null}
        </div>

        {m2.tarifa_aplicada_id ? (
          <p className="text-[10px] text-muted-foreground/70 italic">
            Tarifa aplicada:{" "}
            <span className="font-mono">{m2.tarifa_aplicada_id}</span>
          </p>
        ) : null}
      </div>
    </DetalleSection>
  );
}
