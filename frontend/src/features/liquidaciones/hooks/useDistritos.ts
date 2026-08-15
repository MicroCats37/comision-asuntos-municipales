/**
 * Hook para obtener distritos desde ubigeo.
 * Endpoint: GET /entidades/ubigeo/distritos
 * Backend: ApiResponse[DistritosResponseOut] { items: [{ id, nombre, ubigeo, provincia: { id, nombre }, departamento: { id, nombre } }], total }
 */
import { useApiQuery } from "@/hooks";
import {
  type DistritoOption,
  type DistritosResponse,
  DistritosResponseSchema,
} from "../schemas/distrito.schema";

export function useDistritos(search?: string) {
  return useApiQuery<DistritosResponse, DistritoOption[]>({
    queryKey: ["entidades", "distritos", search || ""],
    url: "/entidades/ubigeo/distritos",
    schema: DistritosResponseSchema,
    params: search ? { search } : undefined,
    queryOptions: {
      staleTime: 1000 * 60 * 1,
      select: (envelope) => {
        if (!envelope.data?.items) return [] as DistritoOption[];
        return envelope.data.items.map((d) => ({
          id: d.id,
          nombre: d.nombre,
          provinciaNombre: d.provincia.nombre,
          departamentoNombre: d.departamento.nombre,
        }));
      },
    },
  });
}
