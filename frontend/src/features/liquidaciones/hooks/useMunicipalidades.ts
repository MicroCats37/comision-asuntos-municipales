/**
 * Hook para obtener municipalidades disponibles para liquidaciones.
 */
import { useApiQuery } from "@/hooks";
import {
  type MunicipalidadData,
  type MunicipalidadesResponse,
  MunicipalidadesResponseSchema,
} from "../schemas/municipalidad.schema";

export function useMunicipalidades() {
  return useApiQuery<MunicipalidadesResponse, MunicipalidadData[]>({
    queryKey: ["entidades", "municipalidades"],
    // Cache-buster: evita servir la respuesta vieja (IDs de antes del reseed).
    url: "/entidades/municipalidades?v=2",
    schema: MunicipalidadesResponseSchema,
    queryOptions: {
      staleTime: 1000 * 60 * 1,
      select: (envelope) => {
        if (!envelope.data) return [];
        return Array.isArray(envelope.data)
          ? envelope.data
          : envelope.data.items;
      },
    },
  });
}
