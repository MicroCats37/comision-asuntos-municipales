/**
 * Hook para obtener las operatividades vigentes de un delegado por CIP.
 * Endpoint: GET /delegados/operatividades-vigentes?cip={cip}
 *
 * Retorna todas las DelegadoOperacion activas con:
 * municipalidad, tipo_liquidacion, especialidad, tipo (TITULAR/ALTERNO), y periodo de vigencia.
 */
import { useApiQuery } from "@/hooks";
import type {
  DelegadoOperacionVigente,
  DelegadoOperatividadesVigentes,
} from "../schemas/rh-delegado-mensual.schema";
import { DelegadoOperatividadesVigentesResponseSchema } from "../schemas/rh-delegado-mensual.schema";

interface UseDelegadoOperatividadesVigentesProps {
  cip: string;
  enabled?: boolean;
}

export function useDelegadoOperatividadesVigentes({
  cip,
  enabled = true,
}: UseDelegadoOperatividadesVigentesProps) {
  const query = useApiQuery({
    queryKey: ["delegados", "operatividades-vigentes", cip],
    url: cip.length > 0 ? "/delegados/operatividades-vigentes" : null,
    schema: DelegadoOperatividadesVigentesResponseSchema,
    params: cip.length > 0 ? { cip } : undefined,
    queryOptions: {
      enabled: enabled && cip.length === 6,
      retry: false,
      select: (data): DelegadoOperatividadesVigentes | null => {
        if (!data?.data) return null;
        return data.data as DelegadoOperatividadesVigentes;
      },
    },
  });

  return {
    ...query,
    operatividades:
      query.data?.operatividades ?? ([] as DelegadoOperacionVigente[]),
    delegadoId: query.data?.delegado_id ?? null,
    nombreCompleto: query.data?.nombre_completo ?? null,
    cipRespuesta: query.data?.cip ?? null,
  };
}
