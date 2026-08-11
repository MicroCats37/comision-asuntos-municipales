import { useLiquidacionList, type LiquidacionFiltros } from './useLiquidacionList';
import { liquidacionInspeccionObraListItemSchema } from '../schemas';

export function useLiquidacionesInspeccionObra(filtros?: LiquidacionFiltros) {
  return useLiquidacionList({
    queryKey: ['liquidaciones', 'inspeccion-obra'],
    url: '/liquidaciones/inspeccion-obra',
    schema: liquidacionInspeccionObraListItemSchema,
    filtros,
  });
}
