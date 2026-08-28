/**
 * Hook para buscar candidatas (liquidaciones sin asignar) para un inspector.
 * Endpoint: GET /finanzas/recibos-inspectores/candidatos?cip={cip}&periodo={periodo}
 */
import { useApiQuery } from "@/hooks";
import type {
  InspectorCandidataItem,
  InspectorCandidatos,
} from "../schemas/rh-inspector-mensual.schema";
import { InspectorCandidatosResponseSchema } from "../schemas/rh-inspector-mensual.schema";

interface UseCandidatasInspectorProps {
  cip: string;
  periodo?: string;
  fecha_inicio?: string;
  fecha_fin?: string;
  enabled?: boolean;
}

interface CandidatasInspectorResult {
  inspector_id: string;
  inspector_nombre: string;
  inspector_cip: string;
  inspector_dni: string;
  periodo: string;
  candidatos: InspectorCandidataItem[];
  total: number;
}

export function useCandidatasInspector({
  cip,
  periodo,
  fecha_inicio,
  fecha_fin,
  enabled = true,
}: UseCandidatasInspectorProps) {
  const params: Record<string, string> = { cip };
  if (periodo) params.periodo = periodo;
  if (fecha_inicio) params.fecha_inicio = fecha_inicio;
  if (fecha_fin) params.fecha_fin = fecha_fin;

  const query = useApiQuery({
    queryKey: [
      "finanzas",
      "recibos-inspectores",
      "candidatos",
      cip,
      periodo ?? "all",
      fecha_inicio ?? "no-inicio",
      fecha_fin ?? "no-fin",
    ],
    url: "/finanzas/recibos-inspectores/candidatos",
    schema: InspectorCandidatosResponseSchema,
    params,
    queryOptions: {
      enabled: enabled && cip.length > 0,
      retry: false,
      select: (data): CandidatasInspectorResult | null => {
        if (!data?.data) return null;
        return data.data as CandidatasInspectorResult;
      },
    },
  });

  return {
    ...query,
    items: query.data?.candidatos ?? ([] as InspectorCandidataItem[]),
    total: query.data?.total ?? 0,
    inspector: query.data
      ? {
          id: query.data.inspector_id,
          nombre: query.data.inspector_nombre,
          cip: query.data.inspector_cip,
          dni: query.data.inspector_dni,
        }
      : null,
  };
}
