import type { ZodType, z } from "zod";
import { useApiQuery } from "@/hooks/callsApi/useApiQuery";
import { useUrlPagination } from "@/hooks/system/useUrlPagination";
import { apiResponseSchema } from "@/types/api.types";
import { paginatedResponseSchema } from "../schemas/liquidacion-base.schema";

type PaginatedData<T> = z.infer<
  ReturnType<typeof paginatedResponseSchema<z.ZodType<T>>>
>;

/** Filtros comunes del backend para listas de liquidaciones. */
export interface LiquidacionFiltros {
  entidad_id?: string;
  distrito_id?: string;
  propietario?: string;
  fecha_desde?: string;
  fecha_hasta?: string;
  numero?: number;
  razon_social?: string;
  direccion?: string;
  /** N.º de documento de la entidad (snapshot del proyecto). */
  documento?: string;
  /** Serie del comprobante VIGENTE de la liquidación. */
  comprobante_serie?: string;
  /** Número del comprobante VIGENTE de la liquidación. */
  comprobante_numero?: string;
}

interface UseLiquidacionListReturn<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  resetPagination: () => void;
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
  const { page, pageSize, setPage, setPageSize, resetPagination } =
    useUrlPagination();

  // Merge pagination + filters
  const params: Record<string, string | number> = {
    page,
    page_size: pageSize,
  };
  if (filtros?.entidad_id) params.entidad_id = filtros.entidad_id;
  if (filtros?.distrito_id) params.distrito_id = filtros.distrito_id;
  if (filtros?.propietario) params.propietario = filtros.propietario;
  if (filtros?.fecha_desde) params.fecha_desde = filtros.fecha_desde;
  if (filtros?.fecha_hasta) params.fecha_hasta = filtros.fecha_hasta;
  if (filtros?.numero) params.numero = filtros.numero;
  if (filtros?.razon_social) params.razon_social = filtros.razon_social;
  if (filtros?.direccion) params.direccion = filtros.direccion;
  if (filtros?.documento) params.documento = filtros.documento;
  if (filtros?.comprobante_serie)
    params.comprobante_serie = filtros.comprobante_serie;
  if (filtros?.comprobante_numero)
    params.comprobante_numero = filtros.comprobante_numero;

  const paginatedSchema = apiResponseSchema(paginatedResponseSchema(schema));

  const {
    data: apiData,
    isLoading,
    isError,
    refetch,
  } = useApiQuery({
    queryKey: [...queryKey, page, pageSize, filtros],
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
    setPage,
    setPageSize,
    resetPagination,
    isLoading,
    isError,
    refetch,
  };
}
