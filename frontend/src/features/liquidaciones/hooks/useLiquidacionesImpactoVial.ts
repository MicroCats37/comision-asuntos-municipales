import { useLiquidacionList, type LiquidacionFiltros } from './useLiquidacionList';
import { liquidacionImpactoVialListItemSchema } from '../schemas';

export function useLiquidacionesImpactoVial(filtros?: LiquidacionFiltros) {
  return useLiquidacionList({
    queryKey: ['liquidaciones', 'impacto-vial'],
    url: '/liquidaciones/impacto-vial',
    schema: liquidacionImpactoVialListItemSchema,
    filtros,
  });
}
