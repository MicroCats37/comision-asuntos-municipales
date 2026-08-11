/**
 * Hook para obtener distritos desde ubigeo.
 * Endpoint: GET /entidades/ubigeo/distritos
 */
import { z } from "zod";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";

const distritoSchema = z.object({
  id: z.string(),
  nombre: z.string(),
  provincia_nombre: z.string(),
  departamento_nombre: z.string(),
});

const distritosPayloadSchema = z.object({
  items: z.array(distritoSchema),
});

const distritosResponseSchema = apiResponseSchema(distritosPayloadSchema);

export function useDistritos(search?: string) {
  return useApiQuery({
    queryKey: ["entidades", "distritos", search || ""],
    url: "/entidades/ubigeo/distritos",
    schema: distritosResponseSchema,
    params: search ? { search } : undefined,
    queryOptions: {
      staleTime: 1000 * 60 * 10,
      select: (envelope) => envelope.data?.items ?? [],
    },
  });
}
