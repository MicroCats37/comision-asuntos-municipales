import { liquidacionImpactoVialListItemSchema } from "../schemas";
import {
  type LiquidacionFiltros,
  useLiquidacionList,
} from "./useLiquidacionList";

export function useLiquidacionesImpactoVial(filtros?: LiquidacionFiltros) {
  return useLiquidacionList({
    queryKey: ["liquidaciones", "impacto-vial"],
    url: "/liquidaciones/impacto-vial",
    schema: liquidacionImpactoVialListItemSchema,
    filtros,
  });
}
