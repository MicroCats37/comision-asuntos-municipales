/**
 * Hook para obtener especialidades vigentes filtradas por tipo de liquidación.
 * El backend consulta el grupo EspecialidadesLiquidacion vigente.
 *
 * Tipos soportados (slugs):
 * - habilitacion-urbana
 * - mecanica-suelos
 * - impacto-vial
 * - taludes
 * - inspeccion-obra
 * - edificacion
 */

import { z } from "zod";
import { useApiQuery } from "@/hooks";
import { apiResponseSchema } from "@/types/api.types";
import { EspecialidadBasica } from "../types/revisiones-vigentes";

const especialidadBasicaPayloadSchema = z.object({
  id: z.string(),
  nombre: z.string(),
});

const especialidadesCatalogoPayloadSchema = z.object({
  items: z.array(especialidadBasicaPayloadSchema),
});

const especialidadesCatalogoResponseSchema = apiResponseSchema(
  especialidadesCatalogoPayloadSchema,
);

export type EspecialidadesCatalogoData = {
  items: EspecialidadBasica[];
};

export function useEspecialidadesVigentesLiquidacion(tipoLiquidacion: string | null) {
  const params = tipoLiquidacion ? { tipo_liquidacion: tipoLiquidacion } : undefined;

  const query = useApiQuery<
    z.infer<typeof especialidadesCatalogoResponseSchema>,
    EspecialidadesCatalogoData
  >({
    queryKey: ["liquidaciones", "especialidades-vigentes", tipoLiquidacion],
    url: "/liquidaciones/especialidades-vigentes",
    schema: especialidadesCatalogoResponseSchema,
    params,
    queryOptions: {
      enabled: !!tipoLiquidacion,
      staleTime: 1000 * 60 * 5, // 5 minutes
      select: (data) => {
        if (!data.data) return { items: [] as EspecialidadBasica[] };
        return data.data as EspecialidadesCatalogoData;
      },
    },
  });

  return query;
}
