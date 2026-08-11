import { useLiquidacionList } from './useLiquidacionList';
import { liquidacionMecanicaSuelosListItemSchema } from '../schemas';

export function useLiquidacionesMecanicaSuelos() {
  return useLiquidacionList({
    queryKey: ['liquidaciones', 'mecanica-suelos'],
    url: '/liquidaciones/mecanica-suelos',
    schema: liquidacionMecanicaSuelosListItemSchema,
  });
}
