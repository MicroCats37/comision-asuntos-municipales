import { liquidacionTaludesListItemSchema } from "../schemas";
import {
  type LiquidacionFiltros,
  useLiquidacionList,
} from "./useLiquidacionList";

export function useLiquidacionesTaludes(filtros?: LiquidacionFiltros) {
  return useLiquidacionList({
    queryKey: ["liquidaciones", "taludes"],
    url: "/liquidaciones/taludes",
    schema: liquidacionTaludesListItemSchema,
    filtros,
  });
}
