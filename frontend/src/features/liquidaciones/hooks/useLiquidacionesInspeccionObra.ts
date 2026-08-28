import { liquidacionInspeccionObraListItemSchema } from "../schemas";
import {
  type LiquidacionFiltros,
  useLiquidacionList,
} from "./useLiquidacionList";

export function useLiquidacionesInspeccionObra(filtros?: LiquidacionFiltros) {
  return useLiquidacionList({
    queryKey: ["liquidaciones", "inspeccion-obra"],
    url: "/liquidaciones/inspeccion-obra",
    schema: liquidacionInspeccionObraListItemSchema,
    filtros,
  });
}
