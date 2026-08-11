import { useLiquidacionList, type LiquidacionFiltros } from './useLiquidacionList';
import { liquidacionTaludesListItemSchema } from '../schemas';

export function useLiquidacionesTaludes(filtros?: LiquidacionFiltros) {
  return useLiquidacionList({
    queryKey: ['liquidaciones', 'taludes'],
    url: '/liquidaciones/taludes',
    schema: liquidacionTaludesListItemSchema,
    filtros,
  });
}
