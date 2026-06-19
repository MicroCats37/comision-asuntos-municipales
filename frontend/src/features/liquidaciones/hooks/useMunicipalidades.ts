/**
 * Hook para obtener municipalidades disponibles para liquidaciones.
 */
import { z } from "zod";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import type { MunicipalidadOption } from "../types/liquidacion-edificaciones";

const municipalidadSchema = z.object({
  id: z.string(),
  nombre: z.string(),
  codigo: z.string().nullable(),
  provincia: z.object({
    id: z.string(),
    nombre: z.string(),
  }).nullable(),
  distrito: z.object({
    id: z.string(),
    nombre: z.string(),
  }).nullable(),
});

const municipalidadesPayloadSchema = z.union([
  z.array(municipalidadSchema),
  z.object({ items: z.array(municipalidadSchema) }),
]);

const municipalidadesResponseSchema = apiResponseSchema(municipalidadesPayloadSchema);

export function useMunicipalidades() {
  return useApiQuery<
    z.infer<typeof municipalidadesResponseSchema>,
    MunicipalidadOption[]
  >({
    queryKey: ["entidades", "municipalidades"],
    url: "/entidades/municipalidades",
    schema: municipalidadesResponseSchema,
    queryOptions: {
      staleTime: 1000 * 60 * 10,
      select: (envelope) => {
        if (!envelope.data) return [];
        return Array.isArray(envelope.data) ? envelope.data : envelope.data.items;
      },
    },
  });
}
