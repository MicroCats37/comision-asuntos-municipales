import { useLiquidacionList, type LiquidacionFiltros } from './useLiquidacionList';
import { liquidacionEdificacionesListItemSchema } from '../schemas';

export function useLiquidacionesEdificaciones(filtros?: LiquidacionFiltros) {
  return useLiquidacionList({
    queryKey: ['liquidaciones', 'edificaciones'],
    url: '/liquidaciones/edificaciones',
    schema: liquidacionEdificacionesListItemSchema,
    filtros,
  });
}
