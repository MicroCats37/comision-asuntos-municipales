import { useLiquidacionList } from './useLiquidacionList';
import { liquidacionEdificacionesListItemSchema } from '../schemas';

export function useLiquidacionesEdificaciones() {
  return useLiquidacionList({
    queryKey: ['liquidaciones', 'edificaciones'],
    url: '/liquidaciones/edificaciones',
    schema: liquidacionEdificacionesListItemSchema,
  });
}
