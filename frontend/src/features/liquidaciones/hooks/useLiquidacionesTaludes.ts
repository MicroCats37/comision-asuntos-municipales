import { useLiquidacionList } from './useLiquidacionList';
import { liquidacionTaludesListItemSchema } from '../schemas';

export function useLiquidacionesTaludes() {
  return useLiquidacionList({
    queryKey: ['liquidaciones', 'taludes'],
    url: '/liquidaciones/taludes',
    schema: liquidacionTaludesListItemSchema,
  });
}
