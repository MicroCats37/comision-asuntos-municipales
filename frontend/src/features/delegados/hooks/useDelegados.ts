/**
 * Hook para lista de delegados con paginación + filtros.
 * CONTROLADO: recibe page/pageSize como props (la vista los gestiona vía store).
 * Endpoint: GET /delegados/?cip=&municipalidad_id=&capitulo_id=&especialidad_id=&estado=
 */
import { useApiQuery } from "@/hooks";
import {
  type DelegadoFiltros,
  type DelegadoOut,
  delegadosListResponseSchema,
} from "../types/delegados.types";

interface UseDelegadosProps {
  page?: number;
  pageSize?: number;
  filtros?: DelegadoFiltros;
}

const BASE_URL = "/delegados";

export function useDelegados({
  page = 1,
  pageSize = 10,
  filtros,
}: UseDelegadosProps = {}) {
  // Merge pagination + filters into query params
  const params: Record<string, string | number> = {
    page,
    page_size: pageSize,
  };
  if (filtros?.cip) params.cip = filtros.cip;
  if (filtros?.municipalidad_id)
    params.municipalidad_id = filtros.municipalidad_id;
  if (filtros?.capitulo_id) params.capitulo_id = filtros.capitulo_id;
  if (filtros?.especialidad_id)
    params.especialidad_id = filtros.especialidad_id;
  if (filtros?.estado) params.estado = filtros.estado;

  const query = useApiQuery({
    queryKey: ["delegados", page, pageSize, filtros],
    url: BASE_URL,
    schema: delegadosListResponseSchema,
    params,
    queryOptions: {
      select: (data) => {
        if (!data?.data) {
          return {
            items: [] as DelegadoOut[],
            total: 0,
            page,
            page_size: pageSize,
            total_pages: 1,
          };
        }
        return data.data;
      },
    },
  });

  return {
    ...query,
    items: query.data?.items ?? ([] as DelegadoOut[]),
    total: query.data?.total ?? 0,
    page: query.data?.page ?? page,
    pageSize: query.data?.page_size ?? pageSize,
    totalPages: query.data?.total_pages ?? 1,
  };
}
