"use client";

import type { ReactNode } from "react";
import type { M2DatosOut } from "@/features/liquidaciones/schemas/liquidacion-m2.schema";
import type { PorcentajeObraDatosOut } from "@/features/liquidaciones/schemas/liquidacion-porcentaje.schema";
import type { VisitasDatosOut } from "@/features/liquidaciones/schemas/liquidacion-visitas.schema";
import {
  LiquidacionDetalleEdificacionesSection,
  type EdificacionesDetalleDatos,
} from "./LiquidacionDetalleEdificacionesSection";
import { LiquidacionDetalleHabilitacionUrbanaSection } from "./LiquidacionDetalleHabilitacionUrbanaSection";
import { LiquidacionDetalleImpactoVialSection } from "./LiquidacionDetalleImpactoVialSection";
import { LiquidacionDetalleInspeccionObraSection } from "./LiquidacionDetalleInspeccionObraSection";
import { LiquidacionDetalleMecanicaSuelosSection } from "./LiquidacionDetalleMecanicaSuelosSection";
import { LiquidacionDetalleTaludesSection } from "./LiquidacionDetalleTaludesSection";

/** The three polymorphic shapes `liquidacion_tipo` can take. */
export type TipoDetalleData =
  | PorcentajeObraDatosOut
  | M2DatosOut
  | VisitasDatosOut;

/**
 * Maps `tipo_liquidacion.codigo` to its tipo-specific detail section.
 *
 * Single source of truth for the tipo → section dispatch used by every
 * "Ver detalle" modal that renders a polymorphic liquidación (the general
 * modal and the delegado / inspector RH modals). The copies this replaced
 * had drifted apart: the general modal was rendering the Edificaciones
 * section for Taludes / Impacto Vial, and the Habilitación Urbana section
 * for Mecánica de Suelos.
 *
 * Returns `null` for an unknown tipo so the caller can still render the
 * rest of the stack without a tipo-specific block.
 */
export function getTipoDetalleSection(
  tipoCodigo: string | null | undefined,
  liquidacionTipo: TipoDetalleData | null | undefined,
  /** Valor del UIT de la liquidación — lo necesita el motor de visitas
   *  (Inspección de Obra) para derivar el costo por visita. */
  uit?: number | null,
): ReactNode {
  if (!liquidacionTipo) return null;

  switch (tipoCodigo) {
    case "EDIFICACION":
      return (
        <LiquidacionDetalleEdificacionesSection
          // Edificaciones es el único motor con estrategia: el objeto puede
          // traerla (listado/detalle propios) o no (superficies de RH), y la
          // sección lo tolera en ambos casos.
          liquidacionTipo={liquidacionTipo as EdificacionesDetalleDatos}
        />
      );
    case "TALUDES":
      return (
        <LiquidacionDetalleTaludesSection
          liquidacionTipo={liquidacionTipo as PorcentajeObraDatosOut}
        />
      );
    case "IMPACTO_VIAL":
      return (
        <LiquidacionDetalleImpactoVialSection
          liquidacionTipo={liquidacionTipo as PorcentajeObraDatosOut}
        />
      );
    case "HABILITACION_URBANA":
      return (
        <LiquidacionDetalleHabilitacionUrbanaSection
          liquidacionTipo={liquidacionTipo as M2DatosOut}
        />
      );
    case "MECANICA_SUELOS":
      return (
        <LiquidacionDetalleMecanicaSuelosSection
          liquidacionTipo={liquidacionTipo as M2DatosOut}
        />
      );
    case "INSPECCION_OBRA":
      return (
        <LiquidacionDetalleInspeccionObraSection
          liquidacionTipo={liquidacionTipo as VisitasDatosOut}
          uit={uit}
        />
      );
    default:
      return null;
  }
}
