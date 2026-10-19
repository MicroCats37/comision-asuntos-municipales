"use client";

import { FlaskRound } from "lucide-react";
import type { M2DatosOut } from "../../schemas/liquidacion-m2.schema";
import { formatCurrency } from "../liquidacion-ui";
import { TarifaDetailSection, type TarifaParam } from "./TarifaDetailSection";

interface Props {
  liquidacionTipo: M2DatosOut;
}

/**
 * Mecánica de Suelos-specific (M2) param block. Thin wrapper around the
 * shared `TarifaDetailSection` — same shape as HU (motor-m2).
 */
export function LiquidacionDetalleMecanicaSuelosSection({
  liquidacionTipo: lt,
}: Props) {
  const params: TarifaParam[] = [];
  if (lt.area_m2 != null && lt.area_m2 > 0) {
    params.push({
      label: "Área",
      value: `${lt.area_m2.toLocaleString("es-PE")} m²`,
    });
  }
  if (lt.costo_por_m2 != null && lt.costo_por_m2 > 0) {
    params.push({
      label: "Costo / m²",
      value: formatCurrency(lt.costo_por_m2),
    });
  }
  if (lt.derecho_minimo != null && lt.derecho_minimo > 0) {
    params.push({
      label: "Der. Mín.",
      value: formatCurrency(lt.derecho_minimo),
    });
  }
  if (lt.derecho_maximo != null && lt.derecho_maximo > 0) {
    params.push({
      label: "Der. Máx.",
      value: formatCurrency(lt.derecho_maximo),
    });
  }

  return (
    <TarifaDetailSection
      title="Detalle técnico de Mecánica de Suelos"
      icon={FlaskRound}
      params={params}
      emptyText="Sin parámetros de área / tarifa registrados."
    />
  );
}
