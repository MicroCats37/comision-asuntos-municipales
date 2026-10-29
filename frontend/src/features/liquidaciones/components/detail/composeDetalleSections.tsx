"use client";

import type { ReactNode } from "react";
import type {
  LiquidacionDelegadoEnGeneralOutput,
  LiquidacionGeneralOutput,
} from "@/features/liquidaciones/schemas/liquidacion-base.schema";
import type { EdificacionesPorcentajeObraDatosOut } from "@/features/liquidaciones/schemas/liquidacion-edificaciones.schema";
import type { PorcentajeObraDatosOut } from "@/features/liquidaciones/schemas/liquidacion-porcentaje.schema";
import {
  DetalleComercialSection,
  DetalleContactoSection,
  DetalleCotizacionDelegadosSection,
  DetalleDelegadosSection,
  DetalleIdentidadSection,
  DetalleObservacionSection,
  DetalleProyectoSection,
} from "./DetalleSections";

interface ComposeProps {
  lg: LiquidacionGeneralOutput;
  /** PorcentajeObra data (Edif / IV / Taludes). Drives whether the
   *  `Cotización y Delegados` combined section is rendered. */
  lt?: PorcentajeObraDatosOut | EdificacionesPorcentajeObraDatosOut | null;
  /** Tipo-specific section rendered between `DetalleProyectoSection` and the
   *  delegados section. Use the `LiquidacionDetalle<Domain>Section` for
   *  your tipo (Edif / Taludes / IV / HU / MS / IO) — it already wraps the
   *  shared `TarifaDetailSection` so the layout stays uniform across tipos. */
  tipoSection?: ReactNode;
  /** IO does not use delegados — pass `false` to skip. Defaults `true`. */
  showDelegados?: boolean;
  /** Delegados data — pulled from `lg.delegados` by default but can be overridden. */
  delegados?: LiquidacionDelegadoEnGeneralOutput[];
}

/**
 * Composes the standard area-stack of the Ver-Detalle modal:
 *   Identidad → Proyecto → [TipoSpec] → [Cotización|Delegados] → Comercial → Contacto → Observación
 *
 * The `tipoSection` slot is the only place that varies per tipo — the caller
 * passes one of the `LiquidacionDetalle<Domain>Section` components which
 * internally use the shared `TarifaDetailSection` wrapper. This keeps the
 * layout uniform across the 6 tipos (Edif / Taludes / IV / HU / MS / IO).
 *
 * Each card / view calls this helper and passes the result as `children` to
 * `<LiquidacionDetalleModal>`. Keeps the views thin and the order
 * consistent across tipos.
 */
export function composeDetalleSections({
  lg,
  lt,
  tipoSection,
  showDelegados = true,
  delegados,
}: ComposeProps): ReactNode {
  const delegadosData = delegados ?? lg.delegados;

  return (
    <>
      <DetalleIdentidadSection lg={lg} />
      <DetalleProyectoSection lg={lg} />

      {/* Per-tipo section (Edif / Taludes / IV / HU / MS / IO) — each caller
          passes its own TarifaDetailSection-wrapped component. */}
      {tipoSection}

      {/* Cotización + Delegados combined — one section that surfaces
          the tarifa ↔ delegado ↔ especialidad relationship. Only when
          the liquidación has PorcentajeObra data (Edif / IV / Taludes). */}
      {lt ? (
        <div className="lg:col-span-12">
          <DetalleCotizacionDelegadosSection
            lt={lt}
            delegados={delegadosData}
          />
        </div>
      ) : null}

      {/* Delegados only when at least one is assigned AND no PorcentajeObra
          (delegados already shown inside CotizacionDelegadosSection for PO). */}
      {!lt && showDelegados && delegadosData.length > 0 ? (
        <div className="lg:col-span-12">
          <DetalleDelegadosSection delegados={delegadosData} />
        </div>
      ) : null}

      <DetalleComercialSection lg={lg} />
      <DetalleContactoSection lg={lg} />
      {lg.observacion ? (
        <DetalleObservacionSection observacion={lg.observacion} />
      ) : null}
    </>
  );
}
