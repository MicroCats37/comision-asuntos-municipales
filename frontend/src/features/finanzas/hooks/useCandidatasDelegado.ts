/**
 * Hook para buscar candidatas (liquidaciones sin asignar) para un delegado.
 * Endpoint: GET /delegados/candidatas?cip={cip}
 */
import { useApiQuery } from "@/hooks";
import type {
  CandidataDelegado,
  DelegadoMinimal,
} from "../schemas/rh-delegado-mensual.schema";
import { DelegadoCandidatasResponseSchema } from "../schemas/rh-delegado-mensual.schema";

interface UseCandidatasDelegadoProps {
  cip: string;
  fecha_inicio?: string;
  fecha_fin?: string;
  enabled?: boolean;
}

interface CandidatasResult {
  delegado: DelegadoMinimal;
  candidatas: CandidataDelegado[];
  total: number;
}

export function useCandidatasDelegado({
  cip,
  fecha_inicio,
  fecha_fin,
  enabled = true,
}: UseCandidatasDelegadoProps) {
  const params: Record<string, string> = { cip };
  if (fecha_inicio) params.fecha_inicio = fecha_inicio;
  if (fecha_fin) params.fecha_fin = fecha_fin;

  const query = useApiQuery({
    queryKey: [
      "delegados",
      "candidatas",
      cip,
      fecha_inicio ?? "no-inicio",
      fecha_fin ?? "no-fin",
    ],
    url: "/delegados/candidatas",
    schema: DelegadoCandidatasResponseSchema,
    params,
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
