import type { ZodType, z } from "zod";
import { useApiQuery } from "@/hooks/callsApi/useApiQuery";
import { usePagination } from "@/hooks/system/usePagination";
import { apiResponseSchema } from "@/types/api.types";
import { paginatedResponseSchema } from "../schemas/liquidacion-base.schema";

type PaginatedData<T> = z.infer<
  ReturnType<typeof paginatedResponseSchema<z.ZodType<T>>>
>;

/** Filtros comunes del backend para listas de liquidaciones. */
export interface LiquidacionFiltros {
  entidad_id?: string;
  propietario?: string;
  fecha_desde?: string;
  fecha_hasta?: string;
  numero?: number;
  razon_social?: string;
  creado_por?: string;
  numero_revisiones?: number;
}

interface UseLiquidacionListReturn<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
}

export function useLiquidacionList<T>({
  queryKey,
  url,
  schema,
  filtros,
}: {
  queryKey: string[];
  url: string;
  schema: ZodType<T>;
  filtros?: LiquidacionFiltros;
}): UseLiquidacionListReturn<T> {
  const { page, pageSize, onPageChange, onPageSizeChange, paginationParams } =
    usePagination();

  // Merge pagination + filters
  const params: Record<string, string | number> = {
    ...paginationParams,
  };
  if (filtros?.entidad_id) params.entidad_id = filtros.entidad_id;
  if (filtros?.propietario) params.propietario = filtros.propietario;
  if (filtros?.fecha_desde) params.fecha_desde = filtros.fecha_desde;
  if (filtros?.fecha_hasta) params.fecha_hasta = filtros.fecha_hasta;
  if (filtros?.numero) params.numero = filtros.numero;
  if (filtros?.razon_social) params.razon_social = filtros.razon_social;
  if (filtros?.creado_por) params.creado_por = filtros.creado_por;
  if (filtros?.numero_revisiones)
    params.numero_revisiones = filtros.numero_revisiones;

  const paginatedSchema = apiResponseSchema(paginatedResponseSchema(schema));

  const {
    data: apiData,
    isLoading,
    isError,
    refetch,
  } = useApiQuery({
    queryKey: [
      ...queryKey,
      paginationParams.page,
      paginationParams.page_size,
      filtros,
    ],
    url,
    params,
    schema: paginatedSchema as ZodType<{
      success: boolean;
      data: PaginatedData<T>;
      error: unknown;
    }>,
  });

  const data = apiData?.data;

  return {
    items: data?.items ?? [],
    total: data?.total ?? 0,
    page,
    pageSize,
    totalPages: data?.total_pages ?? 0,
    setPage: onPageChange,
    setPageSize: onPageSizeChange,
    isLoading,
    isError,
    refetch,
  };
}
