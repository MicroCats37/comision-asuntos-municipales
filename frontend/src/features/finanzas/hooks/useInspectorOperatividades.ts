import { useApiQuery } from "@/hooks";
import {
  type InspectorOperacion,
  InspectorOperatividadesResponseSchema,
} from "../schemas/rh-inspector-mensual.schema";

interface UseInspectorOperatividadesProps {
  cip: string;
  vigente?: boolean;
  enabled?: boolean;
}

/** Operatividades disponibles para la selección de RH mensual de inspector. */
export function useInspectorOperatividades({
  cip,
  vigente,
  enabled = true,
}: UseInspectorOperatividadesProps) {
  return useApiQuery({
    queryKey: [
      "finanzas",
      "recibos-inspectores",
      "operatividades",
      cip,
      vigente,
    ],
    url: cip.length > 0 ? "/finanzas/recibos-inspectores/operatividades" : null,
    params:
      cip.length > 0
        ? { cip, ...(vigente === undefined ? {} : { vigente }) }
        : undefined,
    schema: InspectorOperatividadesResponseSchema,
    queryOptions: {
      enabled: enabled && cip.length === 6,
      retry: false,
      select: (data): InspectorOperacion[] => data.data?.inspectores ?? [],
    },
  });
}
