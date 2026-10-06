/**
 * Hook para editar una liquidación de Impacto Vial.
 *
 * Endpoint: PATCH /liquidaciones/impacto-vial/{id}
 * Payload:   { liquidacion_general?, liquidacion_tipo? }
 *
 * Reutiliza useApiUpdate en modo directo (PATCH) con payload builder.
 * Estructura idéntica a Edificaciones/Taludes (motor PorcentajeObra).
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
import type { LiquidacionImpactoVialListItem } from "../schemas/liquidacion-impacto-vial.schema";
import type { ImpactoVialFormData } from "../schemas/liquidacion-impacto-vial-form.schema";
import { buildPOEditPayload } from "../schemas/liquidacion-po-edit.schema";
import { getLiquidacionEditEndpoint } from "../utils/liquidacionEditEndpoints";

const TIPO: "impacto-vial" = "impacto-vial";
const LIST_KEY = ["liquidaciones", "impacto-vial"] as const;

function buildPayload(data: ImpactoVialFormData): PorcentajeObraEditPayload {
  return buildPOEditPayload(data);
}

export function useEditarImpactoVial(id: string) {
  const baseUrl = getLiquidacionEditEndpoint(TIPO);
  const queryClient = useQueryClient();

  const mutation = useApiUpdate<unknown, PorcentajeObraEditPayload>({
    url: `${baseUrl}/${id}`,
    method: "PATCH",
    schema: PorcentajeObraEditPayloadSchema,
    options: {
      onSuccess: (rawUpdated) => {
        const updatedItem = rawUpdated as LiquidacionImpactoVialListItem;
        // List cache is keyed by [prefix, page, page_size, filtros]; the exact
        // key is unknown here, so invalidate the prefix to refetch all variants.
        queryClient.invalidateQueries({ queryKey: LIST_KEY });
        queryClient.setQueryData(
          ["liquidaciones", "impacto-vial", "detalle", id],
          updatedItem,
        );
      },
    },
  });

  const editar = useMemo(
    () => ({
      ...mutation,
      mutate: (data: ImpactoVialFormData) => {
        mutation.mutate(buildPayload(data));
      },
      mutateAsync: async (data: ImpactoVialFormData) => {
        return mutation.mutateAsync(buildPayload(data));
      },
    }),
    [mutation],
  );

  return editar;
}
