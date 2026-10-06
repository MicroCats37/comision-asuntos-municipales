/**
 * Hook para buscar candidatas (liquidaciones sin asignar) para un delegado.
 *
 * SmartField path (preferido):
 *   GET /delegados/candidatas?delegado_operacion_id={id}&cip={cip}&page=1&page_size=10
 *
 * Filter-based path (legacy):
 *   GET /delegados/candidatas?cip={cip}&municipalidad_id={id}&tipo_liquidacion_id={id}&tipo_delegado={tipo}
 *
 * Module 2: agrega soporte para paginación y filtros de texto.
 * Params nuevos: page, page_size, expediente, numero, propietario, direccion
 *
 * Cuando se usa SmartField (delegado_operacion_id), el backend resuelve la operación directamente
 * y usa su municipalidad/especialidad/tipo para filtrar candidatas. No requiere tipo_liquidacion_id.
 */
import { useApiQuery } from "@/hooks";
import type {
  CandidataDelegado,
  DelegadoCandidatasPaginated,
  DelegadoMinimal,
} from "../schemas/rh-delegado-mensual.schema";
import { DelegadoCandidatasPaginatedResponseSchema } from "../schemas/rh-delegado-mensual.schema";

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
  /** Página de resultados (1-indexed). Default: 1 */
  page?: number;
  /** Cantidad de resultados por página. Default: 10 */
  pageSize?: number;
  /** Filtrar por número de expediente (texto libre). */
  expediente?: string;
  /** Filtrar por número de revisión. */
  numero?: number | string;
  /** Filtrar por nombre de propietario. */
  propietario?: string;
  /** Filtrar por dirección. */
  direccion?: string;
  enabled?: boolean;
}

interface CandidatasResult {
  delegado: DelegadoMinimal;
  candidatas: CandidataDelegado[];
  items: CandidataDelegado[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  page_size: number;
}

export function useCandidatasDelegado({
  cip,
  delegado_operacion_id,
  municipalidad_id,
  tipo_liquidacion_id,
  tipo_delegado,
  fecha_inicio,
  fecha_fin,
  page = 1,
  pageSize = 10,
  expediente,
  numero,
  propietario,
  direccion,
  enabled = true,
}: UseCandidatasDelegadoProps) {
  const params: Record<string, string | number> = {
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

  // Pagination
  params.page = page;
  params.page_size = pageSize;
  // Filters
  if (expediente) params.expediente = expediente;
  if (numero !== undefined && numero !== null && numero !== "")
    params.numero = typeof numero === "string" ? Number(numero) : numero;
  if (propietario) params.propietario = propietario;
  if (direccion) params.direccion = direccion;

  const queryKey: (string | number | undefined)[] = delegado_operacion_id
    ? [
        "delegados",
        "candidatas",
        "by-id",
        delegado_operacion_id,
        cip,
        fecha_inicio ?? "no-inicio",
        fecha_fin ?? "no-fin",
        page,
        pageSize,
        expediente ?? "no-expediente",
        numero ?? "no-numero",
        propietario ?? "no-propietario",
        direccion ?? "no-direccion",
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
        page,
        pageSize,
        expediente ?? "no-expediente",
        numero ?? "no-numero",
        propietario ?? "no-propietario",
        direccion ?? "no-direccion",
      ];

  // SmartField path: enabled cuando hay cip + delegado_operacion_id
  // Filter-based path: enabled cuando hay cip + municipalidad_id + tipo_liquidacion_id + tipo_delegado
  const isEnabledSmartField = !!(
    enabled &&
    cip.length > 0 &&
    delegado_operacion_id
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
    schema: DelegadoCandidatasPaginatedResponseSchema,
    params,
    queryOptions: {
      enabled: isEnabledSmartField || isEnabledFilterBased,
      retry: false,
      select: (data): CandidatasResult | null => {
        if (!data?.data) return null;
        const typed = data.data as DelegadoCandidatasPaginated;
        return {
          delegado: typed.delegado,
          candidatas: typed.items,
          items: typed.items,
          total: typed.total,
          page: typed.page,
          pageSize: typed.page_size,
          totalPages: typed.total_pages,
          page_size: typed.page_size,
        };
      },
    },
  });

  return {
    ...query,
    items: query.data?.items ?? ([] as CandidataDelegado[]),
    candidatas: query.data?.candidatas ?? ([] as CandidataDelegado[]),
    total: query.data?.total ?? 0,
    page: query.data?.page ?? page,
    pageSize: query.data?.pageSize ?? pageSize,
    totalPages: query.data?.totalPages ?? 1,
    delegado: query.data?.delegado ?? null,
  };
}
