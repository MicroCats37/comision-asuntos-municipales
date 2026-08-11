import { useLiquidacionList } from './useLiquidacionList';
import { liquidacionInspeccionObraListItemSchema } from '../schemas';

export function useLiquidacionesInspeccionObra() {
  return useLiquidacionList({
    queryKey: ['liquidaciones', 'inspeccion-obra'],
    url: '/liquidaciones/inspeccion-obra',
    schema: liquidacionInspeccionObraListItemSchema,
  });
}
