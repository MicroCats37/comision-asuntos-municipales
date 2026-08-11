import { useLiquidacionList } from './useLiquidacionList';
import { liquidacionImpactoVialListItemSchema } from '../schemas';

export function useLiquidacionesImpactoVial() {
  return useLiquidacionList({
    queryKey: ['liquidaciones', 'impacto-vial'],
    url: '/liquidaciones/impacto-vial',
    schema: liquidacionImpactoVialListItemSchema,
  });
}
