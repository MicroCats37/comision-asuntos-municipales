import {
  Building2,
  Car,
  FileText,
  HardHat,
  Home,
  type LucideIcon,
  Mountain,
} from "lucide-react";

/**
 * Mapeo de código de tipo_liquidacion → { label, icon }.
 * Usado por LiquidacionDetalleModal y el botón "Ver detalle" para armar
 * automáticamente el badge/header del modal sin que el caller tenga que
 * pasar kindBadge/kindIcon hardcoded.
 *
 * Si el codigo no está en el mapa, devuelve un fallback genérico.
 */
export const TIPO_LIQUIDACION_INFO: Record<
  string,
  { label: string; icon: LucideIcon }
> = {
  EDIFICACION: { label: "Edificación", icon: Building2 },
  HABILITACION_URBANA: { label: "Habilitación Urbana", icon: Home },
  MECANICA_SUELOS: { label: "Mecánica de Suelos", icon: Mountain },
  TALUDES: { label: "Taludes", icon: Mountain },
  IMPACTO_VIAL: { label: "Impacto Vial", icon: Car },
  INSPECCION_OBRA: { label: "Inspección de Obra", icon: HardHat },
};

const FALLBACK = { label: "Liquidación", icon: FileText };

export function getLiquidacionTipoInfo(
  codigo: string | null | undefined,
): { label: string; icon: LucideIcon } {
  if (!codigo) return FALLBACK;
  return TIPO_LIQUIDACION_INFO[codigo] ?? { label: codigo, icon: FileText };
}
