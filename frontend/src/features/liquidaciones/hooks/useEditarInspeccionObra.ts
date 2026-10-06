/**
 * Hook para editar una liquidación de Inspección de Obra.
 *
 * Endpoint: PATCH /liquidaciones/inspeccion-obra/{id}
 * Payload:   { liquidacion_general?, liquidacion_tipo? }
 *
 * Motor Visitas: liquidacion_tipo { datos: { cantidad_visitas, categoria }, tarifa: { tarifa_visitas_id } }
 *
 * onSuccess.sync: sincroniza el item actualizado en cache de lista y detalle,
 * reemplazando el objeto antiguo (comportamiento homogeneizado con creación).
 */

import { useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { useApiUpdate } from "@/hooks/callsApi/useApiUpdate";
import {
  type VisitasEditPayload,
  VisitasEditPayloadSchema,
} from "../schemas/liquidacion-edit-payloads.schema";
import type { LiquidacionInspeccionObraListItem } from "../schemas/liquidacion-inspeccion-obra.schema";
import { buildVisitasEditPayload } from "../schemas/liquidacion-visitas-edit.schema";
import type { VisitasFormData } from "../schemas/liquidacion-visitas-form.schema";
import { getLiquidacionEditEndpoint } from "../utils/liquidacionEditEndpoints";

const TIPO: "inspeccion-obra" = "inspeccion-obra";
const LIST_KEY = ["liquidaciones", "inspeccion-obra"] as const;

function buildPayload(data: VisitasFormData): VisitasEditPayload {
  return buildVisitasEditPayload(data);
}

export function useEditarInspeccionObra(id: string) {
  const baseUrl = getLiquidacionEditEndpoint(TIPO);
  const queryClient = useQueryClient();

  const mutation = useApiUpdate<unknown, VisitasEditPayload>({
    url: `${baseUrl}/${id}`,
    method: "PATCH",
    schema: VisitasEditPayloadSchema,
    options: {
      onSuccess: (rawUpdated) => {
        const updatedItem = rawUpdated as LiquidacionInspeccionObraListItem;
        // List cache is keyed by [prefix, page, page_size, filtros]; the exact
        // key is unknown here, so invalidate the prefix to refetch all variants.
        queryClient.invalidateQueries({ queryKey: LIST_KEY });
        queryClient.setQueryData(
          ["liquidaciones", "inspeccion-obra", "detalle", id],
          updatedItem,
        );
      },
    },
  });

  const editar = useMemo(
    () => ({
      ...mutation,
      mutate: (data: VisitasFormData) => {
        mutation.mutate(buildPayload(data));
      },
      mutateAsync: async (data: VisitasFormData) => {
        return mutation.mutateAsync(buildPayload(data));
      },
    }),
    [mutation],
  );

  return editar;
}
