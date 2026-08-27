/**
 * Hook para buscar candidatas (liquidaciones sin asignar) para un delegado.
 * Endpoint: GET /delegados/candidatas?cip={cip}
 */
import { useApiQuery } from "@/hooks";
import type { CandidataDelegado, DelegadoMinimal } from "../schemas/rh-delegado-mensual.schema";
import { DelegadoCandidatasResponseSchema } from "../schemas/rh-delegado-mensual.schema";

interface UseCandidatasDelegadoProps {
  cip: string;
  enabled?: boolean;
}

interface CandidatasResult {
  delegado: DelegadoMinimal;
  candidatas: CandidataDelegado[];
  total: number;
}

export function useCandidatasDelegado({
  cip,
  enabled = true,
}: UseCandidatasDelegadoProps) {
  const query = useApiQuery({
    queryKey: ["delegados", "candidatas", cip],
    url: "/delegados/candidatas",
    schema: DelegadoCandidatasResponseSchema,
    params: { cip },
    queryOptions: {
      enabled: enabled && cip.length > 0,
      retry: false,
      select: (data): CandidatasResult | null => {
        if (!data?.data) return null;
        return data.data as CandidatasResult;
      },
    },
  });

  return {
    ...query,
    items: query.data?.candidatas ?? ([] as CandidataDelegado[]),
    total: query.data?.total ?? 0,
    delegado: query.data?.delegado ?? null,
  };
}
