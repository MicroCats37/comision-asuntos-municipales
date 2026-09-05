/**
 * Hook para editar una liquidación de Habilitación Urbana.
 *
 * Endpoint: PATCH /liquidaciones/habilitacion-urbana/{id}
 * Payload:   { liquidacion_general?, liquidacion_tipo? }
 *
 * Motor M2: liquidacion_tipo { datos: { area_solicitada }, tarifa: { tarifa_m2_id } }
 *
 * onSuccess.sync: sincroniza el item actualizado en cache de lista y detalle,
 * reemplazando el objeto antiguo (comportamiento homogeneizado con creación).
 */

import { useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { useApiUpdate } from "@/hooks/callsApi/useApiUpdate";
import {
  type M2EditPayload,
  M2EditPayloadSchema,
} from "../schemas/liquidacion-edit-payloads.schema";
import type { LiquidacionHabilitacionUrbanaListItem } from "../schemas/liquidacion-habilitacion-urbana.schema";
import type { HabilitacionUrbanaFormData } from "../schemas/liquidacion-habilitacion-urbana-form.schema";
import { buildM2EditPayload } from "../schemas/liquidacion-m2-edit.schema";
import { getLiquidacionEditEndpoint } from "../utils/liquidacionEditEndpoints";

const TIPO: "habilitacion-urbana" = "habilitacion-urbana";
const LIST_KEY = ["liquidaciones", "habilitacion-urbana"] as const;

function buildPayload(data: HabilitacionUrbanaFormData): M2EditPayload {
  return buildM2EditPayload(data);
}

export function useEditarHabilitacionUrbana(id: string) {
  const baseUrl = getLiquidacionEditEndpoint(TIPO);
  const queryClient = useQueryClient();

  const mutation = useApiUpdate<unknown, M2EditPayload>({
    url: `${baseUrl}/${id}`,
    method: "PATCH",
    schema: M2EditPayloadSchema,
    options: {
      onSuccess: (rawUpdated) => {
        const updatedItem = rawUpdated as LiquidacionHabilitacionUrbanaListItem;
        // List cache is keyed by [prefix, page, page_size, filtros]; the exact
        // key is unknown here, so invalidate the prefix to refetch all variants.
        queryClient.invalidateQueries({ queryKey: LIST_KEY });
        queryClient.setQueryData(
          ["liquidaciones", "habilitacion-urbana", "detalle", id],
          updatedItem,
        );
      },
    },
  });

  const editar = useMemo(
    () => ({
      ...mutation,
      mutate: (data: HabilitacionUrbanaFormData) => {
        mutation.mutate(buildPayload(data));
      },
      mutateAsync: async (data: HabilitacionUrbanaFormData) => {
        return mutation.mutateAsync(buildPayload(data));
      },
    }),
    [mutation],
  );

  return editar;
}
