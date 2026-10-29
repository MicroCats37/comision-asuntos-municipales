"use client";

import { Building2 } from "lucide-react";
import { formatDecimalPercent } from "@/utils/number-formatter";
import type { PorcentajeObraDatosOut } from "../../schemas/liquidacion-porcentaje.schema";
import type { EstrategiaCotizacionPOOut } from "../../schemas/liquidacion-edificaciones.schema";
import { formatCurrency, formatEnumLabel } from "../liquidacion-ui";
import { TarifaDetailSection, type TarifaParam } from "./TarifaDetailSection";

/**
 * Datos PO que la sección puede leer.
 *
 * El wrapper PO compartido no lleva campos de estrategia: se combinan como
 * opcionales para que Taludes, Impacto Vial y edge (que reutilizan esta
 * sección vía `getTipoDetalleSection`) no cambien de contrato. Solo
 * Edificaciones las trae.
 *
 * `valor_declarado` se relaja a nullable porque en Edificaciones con
 * TOTAL_EXPLICITO es NULL (el total final es el dato autoritativo) y el
 * wrapper compartido lo declara obligatorio.
 */
export type EdificacionesDetalleDatos = Omit<
  PorcentajeObraDatosOut,
  "valor_declarado"
> & {
  valor_declarado?: number | null;
} & Partial<EstrategiaCotizacionPOOut>;

interface Props {
  liquidacionTipo: EdificacionesDetalleDatos;
}

const getTipoTramiteLabel = (value: string | null | undefined): string => {
  switch (value) {
    case "OBRA_NUEVA":
      return "Obra Nueva";
    case "DEMOLICION":
      return "Demolición";
    case "AMPLIACION":
      return "Ampliación";
    case "REMODELACION":
      return "Remodelación";
    case "MODIFICACION_LICENCIA":
      return "Modificación de Licencia";
    case "REINTEGRO":
      return "Reintegro";
    case "PROYECTO_CON_PLANTAS_TIPICAS":
      return "Proyecto con Plantas Típicas";
    default:
      return formatEnumLabel(value);
  }
};

/**
 * Edificaciones-specific (PorcentajeObra) param block in the Ver-Detalle
 * modal. Delegates the entire layout to the shared `TarifaDetailSection`
 * wrapper — it provides the header, trámite chip, params grid and fallback
 * text uniformly across the 6 liquidation tipos.
 *
 * Los motores sin estrategia (Taludes, Impacto Vial, edge) no pasan ningún
 * campo de estrategia: el bloque de contexto simplemente no se renderiza y su
 * contrato de UI queda intacto.
 */
export function LiquidacionDetalleEdificacionesSection({
  liquidacionTipo: lt,
}: Props) {
  const params: TarifaParam[] = [];
  if (lt.valor_declarado != null && lt.valor_declarado > 0) {
    params.push({
      label: "Valor declarado",
      value: formatCurrency(lt.valor_declarado),
    });
  }
  if (lt.porcentaje_liquidacion != null) {
    params.push({
      label: "% Liq.",
      value: formatDecimalPercent(lt.porcentaje_liquidacion),
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
  if (lt.porcentaje_minimo_uit != null) {
    params.push({
      label: "% Mín. UIT",
      value: formatDecimalPercent(lt.porcentaje_minimo_uit),
    });
  }

  return (
    <TarifaDetailSection
      title="Detalle técnico de Edificación"
      icon={Building2}
      tramiteLabel={
        lt.tipo_tramite != null && lt.tipo_tramite.trim() !== ""
          ? getTipoTramiteLabel(lt.tipo_tramite)
          : undefined
      }
      params={params}
    />
  );
}
