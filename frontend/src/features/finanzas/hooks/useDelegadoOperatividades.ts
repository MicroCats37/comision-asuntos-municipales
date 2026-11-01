/**
 * Hook para obtener las operatividades de un delegado por CIP.
 * Endpoint: GET /delegados/operatividades?cip={cip}&vigente={boolean}
 *
 * Retorna todas las DelegadoOperacion activas con:
 * municipalidad, tipo_liquidacion, especialidad, tipo (TITULAR/ALTERNO), y periodo de vigencia.
 */
import { useApiQuery } from "@/hooks";
import type {
  DelegadoOperacion,
  DelegadoOperatividades,
} from "../schemas/rh-delegado-mensual.schema";
import { DelegadoOperatividadesResponseSchema } from "../schemas/rh-delegado-mensual.schema";

interface UseDelegadoOperatividadesProps {
  cip: string;
  vigente?: boolean;
  enabled?: boolean;
}

export function useDelegadoOperatividades({
  cip,
  vigente,
  enabled = true,
}: UseDelegadoOperatividadesProps) {
  const query = useApiQuery({
    queryKey: ["delegados", "operatividades", cip, vigente],
    url: cip.length > 0 ? "/delegados/operatividades" : null,
    schema: DelegadoOperatividadesResponseSchema,
    params:
      cip.length > 0
        ? { cip, ...(vigente === undefined ? {} : { vigente }) }
        : undefined,
    queryOptions: {
      enabled: enabled && cip.length === 6,
      retry: false,
      select: (data): DelegadoOperatividades | null => {
        if (!data?.data) return null;
        return data.data as DelegadoOperatividades;
      },
    },
  });

  return {
    ...query,
    operatividades: query.data?.operatividades ?? ([] as DelegadoOperacion[]),
    delegadoId: query.data?.delegado_id ?? null,
    nombreCompleto: query.data?.nombre_completo ?? null,
    cipRespuesta: query.data?.cip ?? null,
  };
}
