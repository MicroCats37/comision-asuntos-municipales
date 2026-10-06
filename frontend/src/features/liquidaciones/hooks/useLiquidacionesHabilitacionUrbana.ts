import { liquidacionHabilitacionUrbanaListItemSchema } from "../schemas";
import {
  type LiquidacionFiltros,
  useLiquidacionList,
} from "./useLiquidacionList";

export function useLiquidacionesHabilitacionUrbana(
  filtros?: LiquidacionFiltros,
) {
  return useLiquidacionList({
    queryKey: ["liquidaciones", "habilitacion-urbana"],
    url: "/liquidaciones/habilitacion-urbana",
    schema: liquidacionHabilitacionUrbanaListItemSchema,
    filtros,
  });
}
