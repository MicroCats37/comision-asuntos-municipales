/**
 * Hook para obtener los tipos de liquidación disponibles.
 * Endpoint: GET /delegados/tipos-liquidacion
 */
import { z } from "zod";
import { useApiQuery } from "@/hooks";
import {
  TipoLiquidacionMinimalSchema,
} from "../schemas/liquidacion-base.schema";
import { apiResponseSchema } from "@/types/api.types";

const tiposLiquidacionResponseSchema = apiResponseSchema(
  z.object({
    tipos: z.array(TipoLiquidacionMinimalSchema),
  }),
);

type Zodinfer<T> = T extends z.ZodType<infer U> ? U : never;

export function useTiposLiquidacion() {
  return useApiQuery({
    queryKey: ["delegados", "tipos-liquidacion"],
    url: "/delegados/tipos-liquidacion",
    schema: tiposLiquidacionResponseSchema,
    queryOptions: {
      staleTime: 1000 * 60 * 5,
      select: (envelope): Zodinfer<typeof TipoLiquidacionMinimalSchema>[] => {
        if (!envelope?.data?.tipos) return [];
        return envelope.data.tipos;
      },
    },
  });
}
