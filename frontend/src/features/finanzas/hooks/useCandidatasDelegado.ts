/**
 * Hook para buscar candidatas (liquidaciones sin asignar) para un delegado.
 *
 * SmartField path (preferido):
 *   GET /delegados/candidatas?delegado_operacion_id={id}&cip={cip}&fecha_inicio=...&fecha_fin=...
 *
 * Filter-based path (legacy):
 *   GET /delegados/candidatas?cip={cip}&municipalidad_id={id}&tipo_liquidacion_id={id}&tipo_delegado={tipo}
 *
 * Cuando se usa SmartField (delegado_operacion_id), el backend resuelve la operación directamente
 * y usa su municipalidad/especialidad/tipo para filtrar candidatas. No requiere tipo_liquidacion_id.
 */
import { useApiQuery } from "@/hooks";
import type {
  CandidataDelegado,
  DelegadoMinimal,
} from "../schemas/rh-delegado-mensual.schema";
import { DelegadoCandidatasResponseSchema } from "../schemas/rh-delegado-mensual.schema";

interface UseCandidatasDelegadoProps {
  /** CIP del delegado — requerido para ambos paths */
  cip: string;
  /** ID de la DelegadoOperacion desde SmartField. Si se proporciona, se usa el path directo. */
  delegado_operacion_id?: string;
  /** Filtros legacy (solo necesarios si NO se usa delegado_operacion_id) */
  municipalidad_id?: string;
  tipo_liquidacion_id?: string;
  tipo_delegado?: string;
  /** Filtros de fecha opcionales */
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
  delegado_operacion_id,
  municipalidad_id,
  tipo_liquidacion_id,
  tipo_delegado,
  fecha_inicio,
  fecha_fin,
  enabled = true,
}: UseCandidatasDelegadoProps) {
  const params: Record<string, string> = {
    cip,
  };

  // SmartField path: usa delegado_operacion_id directamente
  if (delegado_operacion_id) {
    params.delegado_operacion_id = delegado_operacion_id;
  } else {
    // Filter-based path legacy
    if (municipalidad_id) params.municipalidad_id = municipalidad_id;
    if (tipo_liquidacion_id) params.tipo_liquidacion_id = tipo_liquidacion_id;
    if (tipo_delegado) params.tipo_delegado = tipo_delegado;
  }

  if (fecha_inicio) params.fecha_inicio = fecha_inicio;
  if (fecha_fin) params.fecha_fin = fecha_fin;

  const queryKey: (string | undefined)[] = delegado_operacion_id
    ? [
        "delegados",
        "candidatas",
        "by-id",
        delegado_operacion_id,
        cip,
        fecha_inicio ?? "no-inicio",
        fecha_fin ?? "no-fin",
      ]
    : [
        "delegados",
        "candidatas",
        "by-filters",
        cip,
        municipalidad_id,
        tipo_liquidacion_id,
        tipo_delegado,
        fecha_inicio ?? "no-inicio",
        fecha_fin ?? "no-fin",
      ];

  // SmartField path: enabled cuando hay cip + delegado_operacion_id
  // Filter-based path: enabled cuando hay cip + municipalidad_id + tipo_liquidacion_id + tipo_delegado
  const isEnabledSmartField = !!(
    enabled && cip.length > 0 && delegado_operacion_id
  );
  const isEnabledFilterBased = !!(
    enabled &&
    cip.length > 0 &&
    municipalidad_id &&
    municipalidad_id.length > 0 &&
    tipo_liquidacion_id &&
    tipo_liquidacion_id.length > 0 &&
    tipo_delegado &&
    tipo_delegado.length > 0
  );

  const query = useApiQuery({
    queryKey,
    url: "/delegados/candidatas",
    schema: DelegadoCandidatasResponseSchema,
    params,
    queryOptions: {
      enabled: isEnabledSmartField || isEnabledFilterBased,
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
