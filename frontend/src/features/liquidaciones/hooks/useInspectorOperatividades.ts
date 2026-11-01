import type { z } from "zod";
import {
  type InspectorOperacionSchema,
  InspectorOperatividadesResponseSchema,
} from "@/features/inspectores/schemas/inspector-vigente.schema";
import { useApiQuery } from "@/hooks";

/**
 * Busca todas las operatividades de un inspector por CIP. Por defecto no
 * aplica vigencia: es útil para asociar documentos históricos.
 */
export function useInspectorOperatividades(
  cip: string,
  vigente?: boolean,
  enabled = false,
) {
  return useApiQuery<
    z.infer<typeof InspectorOperatividadesResponseSchema>,
    z.infer<typeof InspectorOperacionSchema>[]
  >({
    queryKey: ["liquidaciones", "inspectores", "operatividades", cip, vigente],
    url: "/liquidaciones/inspectores/seleccionables-por-cip",
    params: {
      cip,
      ...(vigente === undefined ? {} : { vigente }),
    },
    schema: InspectorOperatividadesResponseSchema,
    queryOptions: {
      enabled: enabled && Boolean(cip),
      staleTime: 0,
      select: (data) => data.data?.inspectores ?? [],
    },
  });
}
