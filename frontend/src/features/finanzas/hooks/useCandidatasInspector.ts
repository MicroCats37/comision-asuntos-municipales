/**
 * Hook para buscar candidatas (liquidaciones sin asignar) para un inspector.
 * Endpoint: GET /finanzas/recibos-inspectores/candidatos?cip={cip}&page=1&page_size=10
 *
 * Module 2: agrega soporte para paginación y filtros de texto.
 * Params nuevos: page, page_size, expediente, numero, propietario, direccion
 */
import { useApiQuery } from "@/hooks";
import type {
  InspectorCandidataItem,
  InspectorCandidatosPaginated,
} from "../schemas/rh-inspector-mensual.schema";
import { InspectorCandidatosPaginatedResponseSchema } from "../schemas/rh-inspector-mensual.schema";

interface UseCandidatasInspectorProps {
  cip: string;
  periodo?: string;
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

interface CandidatasInspectorResult {
  inspector_id: string;
  inspector_nombre: string;
  inspector_cip: string;
  inspector_dni: string;
  periodo: string;
  candidatos: InspectorCandidataItem[];
  items: InspectorCandidataItem[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  page_size: number;
}

export function useCandidatasInspector({
  cip,
  periodo,
  fecha_inicio,
  fecha_fin,
  page = 1,
  pageSize = 10,
  expediente,
  numero,
  propietario,
  direccion,
  enabled = true,
}: UseCandidatasInspectorProps) {
  const params: Record<string, string | number> = { cip };
  if (periodo) params.periodo = periodo;
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

  const query = useApiQuery({
    queryKey: [
      "finanzas",
      "recibos-inspectores",
      "candidatos",
      cip,
      periodo ?? "all",
      fecha_inicio ?? "no-inicio",
      fecha_fin ?? "no-fin",
      page,
      pageSize,
      expediente ?? "no-expediente",
      numero ?? "no-numero",
      propietario ?? "no-propietario",
      direccion ?? "no-direccion",
    ],
    url: "/finanzas/recibos-inspectores/candidatos",
    schema: InspectorCandidatosPaginatedResponseSchema,
    params,
    queryOptions: {
      enabled: enabled && cip.length > 0,
      retry: false,
      select: (data): CandidatasInspectorResult | null => {
        if (!data?.data) return null;
        const typed = data.data as InspectorCandidatosPaginated;
        // Support both legacy .candidatos (current modals) and new .items
        return {
          inspector_id: typed.inspector_id,
          inspector_nombre: typed.inspector_nombre,
          inspector_cip: typed.inspector_cip,
          inspector_dni: typed.inspector_dni,
          periodo: typed.periodo,
          candidatos: typed.items,
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
    items: query.data?.items ?? ([] as InspectorCandidataItem[]),
    candidatos: query.data?.candidatos ?? ([] as InspectorCandidataItem[]),
    total: query.data?.total ?? 0,
    page: query.data?.page ?? page,
    pageSize: query.data?.pageSize ?? pageSize,
    totalPages: query.data?.totalPages ?? 1,
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
