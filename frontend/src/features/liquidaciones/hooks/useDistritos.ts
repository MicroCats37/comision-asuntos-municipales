/**
 * Hook para obtener distritos desde ubigeo.
 * Endpoint: GET /entidades/ubigeo/distritos
 * Backend: ApiResponse[DistritosResponseOut] { items: [{ id, nombre, ubigeo, provincia: { id, nombre }, departamento: { id, nombre } }], total }
 */
import { z } from "zod";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";

const provinciaBasicSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});

const departamentoBasicSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});

const distritoSchema = z.object({
  id: z.string(),
  nombre: z.string(),
  ubigeo: z.string(),
  provincia: provinciaBasicSchema,
  departamento: departamentoBasicSchema,
});

const distritosPayloadSchema = z.object({
  items: z.array(distritoSchema),
  total: z.number(),
});

const distritosResponseSchema = apiResponseSchema(distritosPayloadSchema);

export interface DistritoOption {
  id: string;
  nombre: string;
  provinciaNombre: string;
  departamentoNombre: string;
}

export function useDistritos(search?: string) {
  return useApiQuery({
    queryKey: ["entidades", "distritos", search || ""],
    url: "/entidades/ubigeo/distritos",
    schema: distritosResponseSchema,
    params: search ? { search } : undefined,
    queryOptions: {
      staleTime: 1000 * 60 * 10,
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
