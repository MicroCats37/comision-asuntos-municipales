/**
 * Hook para obtener distritos con filtros.
 * Usa useApiQuery genérico del proyecto.
 */
import { useApiQuery } from "@/hooks";
import {
  type DistritoOption,
  type DistritosResponse,
  DistritosResponseSchema,
} from "../schemas/distrito.schema";

interface UseDistritosProps {
  search?: string;
  provincia_id?: string;
  departamento_id?: string;
  enabled?: boolean;
}

export function useDistritos({
  search,
  provincia_id,
  departamento_id,
  enabled = true,
}: UseDistritosProps = {}) {
  // Build params, excluding undefined values
  const params: Record<string, unknown> = {};
  if (search) params.search = search;
  if (provincia_id) params.provincia_id = provincia_id;
  if (departamento_id) params.departamento_id = departamento_id;

  const queryKey = params ? ["distritos", params] : ["distritos"];

  return useApiQuery<DistritosResponse, DistritoOption[]>({
    queryKey,
    // Cache-buster: evita servir la respuesta vieja cacheada con max-age=1 año.
    url: "/entidades/ubigeo/distritos?v=2",
    schema: DistritosResponseSchema,
    params: Object.keys(params).length > 0 ? params : undefined,
    queryOptions: {
      enabled,
      staleTime: 1000 * 60 * 1,
      select: (data) => {
        if (!data.data?.items) return [];
        return data.data.items;
      },
    },
  });
}
