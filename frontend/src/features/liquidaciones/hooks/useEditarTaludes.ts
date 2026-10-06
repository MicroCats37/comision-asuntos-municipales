/**
 * Hook para editar una liquidación de Taludes.
 *
 * Endpoint: PATCH /liquidaciones/taludes/{id}
 * Payload:   { liquidacion_general?, liquidacion_tipo? }
 *
 * Reutiliza useApiUpdate en modo directo (PATCH) con payload builder.
 * Estructura idéntica a Edificaciones (motor PorcentajeObra).
 *
 * onSuccess.sync: sincroniza el item actualizado en cache de lista y detalle,
 * reemplazando el objeto antiguo (comportamiento homogeneizado con creación).
 */

import { useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { useApiUpdate } from "@/hooks/callsApi/useApiUpdate";
import {
  type PorcentajeObraEditPayload,
  PorcentajeObraEditPayloadSchema,
} from "../schemas/liquidacion-edit-payloads.schema";
import { buildPOEditPayload } from "../schemas/liquidacion-po-edit.schema";
import type { LiquidacionTaludesListItem } from "../schemas/liquidacion-taludes.schema";
import type { TaludesFormData } from "../schemas/liquidacion-taludes-form.schema";
import { getLiquidacionEditEndpoint } from "../utils/liquidacionEditEndpoints";

const TIPO: "taludes" = "taludes";
const LIST_KEY = ["liquidaciones", "taludes"] as const;

function buildPayload(data: TaludesFormData): PorcentajeObraEditPayload {
  return buildPOEditPayload(data);
}

export function useEditarTaludes(id: string) {
  const baseUrl = getLiquidacionEditEndpoint(TIPO);
  const queryClient = useQueryClient();

  const mutation = useApiUpdate<unknown, PorcentajeObraEditPayload>({
    url: `${baseUrl}/${id}`,
    method: "PATCH",
    schema: PorcentajeObraEditPayloadSchema,
    options: {
      onSuccess: (rawUpdated) => {
        const updatedItem = rawUpdated as LiquidacionTaludesListItem;
        // List cache is keyed by [prefix, page, page_size, filtros]; the exact
        // key is unknown here, so invalidate the prefix to refetch all variants.
        queryClient.invalidateQueries({ queryKey: LIST_KEY });
        queryClient.setQueryData(
          ["liquidaciones", "taludes", "detalle", id],
          updatedItem,
        );
      },
    },
  });

  const editar = useMemo(
    () => ({
      ...mutation,
      mutate: (data: TaludesFormData) => {
        mutation.mutate(buildPayload(data));
      },
      mutateAsync: async (data: TaludesFormData) => {
        return mutation.mutateAsync(buildPayload(data));
      },
    }),
    [mutation],
  );

  return editar;
}
