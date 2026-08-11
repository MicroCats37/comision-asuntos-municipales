import { useLiquidacionList } from './useLiquidacionList';
import { liquidacionHabilitacionUrbanaListItemSchema } from '../schemas';

export function useLiquidacionesHabilitacionUrbana() {
  return useLiquidacionList({
    queryKey: ['liquidaciones', 'habilitacion-urbana'],
    url: '/liquidaciones/habilitacion-urbana',
    schema: liquidacionHabilitacionUrbanaListItemSchema,
  });
}
