import { liquidacionEdificacionesListItemSchema } from "../schemas";
import {
  type LiquidacionFiltros,
  useLiquidacionList,
} from "./useLiquidacionList";

export function useLiquidacionesEdificaciones(filtros?: LiquidacionFiltros) {
  return useLiquidacionList({
    queryKey: ["liquidaciones", "edificaciones"],
    url: "/liquidaciones/edificaciones",
    schema: liquidacionEdificacionesListItemSchema,
    filtros,
  });
}
