import { liquidacionMecanicaSuelosListItemSchema } from "../schemas";
import {
  type LiquidacionFiltros,
  useLiquidacionList,
} from "./useLiquidacionList";

export function useLiquidacionesMecanicaSuelos(filtros?: LiquidacionFiltros) {
  return useLiquidacionList({
    queryKey: ["liquidaciones", "mecanica-suelos"],
    url: "/liquidaciones/mecanica-suelos",
    schema: liquidacionMecanicaSuelosListItemSchema,
    filtros,
  });
}
