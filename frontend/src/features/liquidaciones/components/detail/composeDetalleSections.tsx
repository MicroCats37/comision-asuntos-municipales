"use client";

import type { ReactNode } from "react";
import type {
  LiquidacionDelegadoEnGeneralOutput,
  LiquidacionGeneralOutput,
} from "@/features/liquidaciones/schemas/liquidacion-base.schema";
import type { M2DatosOut } from "@/features/liquidaciones/schemas/liquidacion-m2.schema";
import type { PorcentajeObraDatosOut } from "@/features/liquidaciones/schemas/liquidacion-porcentaje.schema";
import type { VisitasDatosOut } from "@/features/liquidaciones/schemas/liquidacion-visitas.schema";
import {
  DetalleAreaTarifaSection,
  DetalleComercialSection,
  DetalleContactoSection,
  DetalleCotizacionDelegadosSection,
  DetalleDelegadosSection,
  DetalleIdentidadSection,
  DetalleObservacionSection,
  DetalleProyectoSection,
  DetalleVisitasSection,
} from "./DetalleSections";

interface ComposeProps {
  lg: LiquidacionGeneralOutput;
  /** PorcentajeObra data (Edif / IV / Taludes). When present, the
   *  Tarifas section is rendered side-by-side with Delegados. */
  lt?: PorcentajeObraDatosOut | null;
  /** M2DatosOut (HU / MS). When present, renders the Área + Tarifa section. */
  m2?: M2DatosOut | null;
  /** VisitasDatosOut (IO). When present, renders the Visitas section
   *  (count + categoría + inspectores summary). */
  visitas?: VisitasDatosOut | null;
  /** Tipo-specific section for non-PorcentajeObra tipos (currently unused —
   *  kept for future tipo-specific content). */
  tipoSection?: ReactNode;
  /** IO does not use delegados — pass `false` to skip. Defaults `true`. */
  showDelegados?: boolean;
  /** Delegados data — pulled from `lg.delegados` by default but can be overridden. */
  delegados?: LiquidacionDelegadoEnGeneralOutput[];
}

/**
 * Composes the standard area-stack of the Ver-Detalle modal:
 *   Identidad → Proyecto → [TipoSpec] → Tarifas|Delegados (parallel) → Comercial → Contacto → Observacion
 *
 * Tipo-specific sections:
 *   - `lt` (PorcentajeObra: Edif/IV/Taludes) → renders Tarifas section
 *   - `m2` (M2: HU/MS) → renders AreaTarifa section
 *   - `visitas` (IO) → renders Visitas section
 *
 * Each card / view calls this helper and passes the result as `children` to
 * `<LiquidacionDetalleModal>`. Keeps the views thin and the order
 * consistent across tipos.
 */
export function composeDetalleSections({
  lg,
  lt,
  m2,
  visitas,
  tipoSection: _tipoSection,
  showDelegados = true,
  delegados,
}: ComposeProps): ReactNode {
  const delegadosData = delegados ?? lg.delegados;

  return (
    <>
      <DetalleIdentidadSection lg={lg} />
      <DetalleProyectoSection lg={lg} />

      {/* Tipo-specific sections (each full-width at lg) */}
      {m2 ? <DetalleAreaTarifaSection m2={m2} /> : null}
      {visitas ? <DetalleVisitasSection visitas={visitas} /> : null}

      {/* Cotización + Delegados combined — one section that surfaces
          the tarifa ↔ delegado ↔ especialidad relationship. */}
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
