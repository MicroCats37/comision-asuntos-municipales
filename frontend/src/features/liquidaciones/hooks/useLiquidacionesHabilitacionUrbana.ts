import { useLiquidacionList, type LiquidacionFiltros } from './useLiquidacionList';
import { liquidacionHabilitacionUrbanaListItemSchema } from '../schemas';

export function useLiquidacionesHabilitacionUrbana(filtros?: LiquidacionFiltros) {
  return useLiquidacionList({
    queryKey: ['liquidaciones', 'habilitacion-urbana'],
    url: '/liquidaciones/habilitacion-urbana',
    schema: liquidacionHabilitacionUrbanaListItemSchema,
    filtros,
  });
}
