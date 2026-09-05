/**
 * Hook para editar una liquidación de Mecánica de Suelos.
 *
 * Endpoint: PATCH /liquidaciones/mecanica-suelos/{id}
 * Payload:   { liquidacion_general?, liquidacion_tipo? }
 *
 * Motor M2: identical structure to Habilitación Urbana.
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
import { buildM2EditPayload } from "../schemas/liquidacion-m2-edit.schema";
import type { LiquidacionMecanicaSuelosListItem } from "../schemas/liquidacion-mecanica-suelos.schema";
import type { MecanicaSuelosFormData } from "../schemas/liquidacion-mecanica-suelos-form.schema";
import { getLiquidacionEditEndpoint } from "../utils/liquidacionEditEndpoints";

const TIPO: "mecanica-suelos" = "mecanica-suelos";
const LIST_KEY = ["liquidaciones", "mecanica-suelos"] as const;

function buildPayload(data: MecanicaSuelosFormData): M2EditPayload {
  return buildM2EditPayload(data);
}

export function useEditarMecanicaSuelos(id: string) {
  const baseUrl = getLiquidacionEditEndpoint(TIPO);
  const queryClient = useQueryClient();

  const mutation = useApiUpdate<unknown, M2EditPayload>({
    url: `${baseUrl}/${id}`,
    method: "PATCH",
    schema: M2EditPayloadSchema,
    options: {
      onSuccess: (rawUpdated) => {
        const updatedItem = rawUpdated as LiquidacionMecanicaSuelosListItem;
        // List cache is keyed by [prefix, page, page_size, filtros]; the exact
        // key is unknown here, so invalidate the prefix to refetch all variants.
        queryClient.invalidateQueries({ queryKey: LIST_KEY });
        queryClient.setQueryData(
          ["liquidaciones", "mecanica-suelos", "detalle", id],
          updatedItem,
        );
      },
    },
  });

  const editar = useMemo(
    () => ({
      ...mutation,
      mutate: (data: MecanicaSuelosFormData) => {
        mutation.mutate(buildPayload(data));
      },
      mutateAsync: async (data: MecanicaSuelosFormData) => {
        return mutation.mutateAsync(buildPayload(data));
      },
    }),
    [mutation],
  );

  return editar;
}
