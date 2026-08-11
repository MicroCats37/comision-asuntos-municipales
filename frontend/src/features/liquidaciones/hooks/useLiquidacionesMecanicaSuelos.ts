import { useLiquidacionList, type LiquidacionFiltros } from './useLiquidacionList';
import { liquidacionMecanicaSuelosListItemSchema } from '../schemas';

export function useLiquidacionesMecanicaSuelos(filtros?: LiquidacionFiltros) {
  return useLiquidacionList({
    queryKey: ['liquidaciones', 'mecanica-suelos'],
    url: '/liquidaciones/mecanica-suelos',
    schema: liquidacionMecanicaSuelosListItemSchema,
    filtros,
  });
}
