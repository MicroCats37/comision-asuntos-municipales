/**
 * Hook para editar una liquidación de Edificaciones.
 *
 * Endpoint: PATCH /liquidaciones/edificaciones/{id}
 * Payload:   { liquidacion_general?, liquidacion_tipo? }
 *
 * Reutiliza useApiUpdate en modo directo (PATCH) con payload builder.
 * No utiliza useGenericUpdateMutation porque el payload es wrapped.
 *
 * onSuccess.sync: sincroniza el item actualizado en cache de lista y detalle,
 * reemplazando el objeto antiguo (comportamiento homogeneizado con creación).
 */

import { useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { useApiUpdate } from "@/hooks/callsApi/useApiUpdate";
import type { LiquidacionEdificacionesListItem } from "../schemas/liquidacion-edificaciones.schema";
import type { EdificacionesFormData } from "../schemas/liquidacion-edificaciones-form.schema";
import {
  type PorcentajeObraEditPayload,
  PorcentajeObraEditPayloadSchema,
} from "../schemas/liquidacion-edit-payloads.schema";
import { buildPOEditPayload } from "../schemas/liquidacion-po-edit.schema";
import { getLiquidacionEditEndpoint } from "../utils/liquidacionEditEndpoints";

const TIPO: "edificacion" = "edificacion";
const LIST_KEY = ["liquidaciones", "edificaciones"] as const;

/**
 * Build the PATCH payload from form data.
 * Uses shared PO payload builder (includes tipo_tramite fix).
 *
 * @param data - The form data
 * @param canEditProyecto - When false, skips proyecto fields from the payload
 */
function buildPayload(
  data: EdificacionesFormData,
  canEditProyecto: boolean = true,
): PorcentajeObraEditPayload {
  return buildPOEditPayload(data, canEditProyecto);
}

export function useEditarEdificaciones(id: string) {
  const baseUrl = getLiquidacionEditEndpoint(TIPO);
  const queryClient = useQueryClient();

  const mutation = useApiUpdate<
    // Response is the full list item, not the edit payload schema
    unknown,
    PorcentajeObraEditPayload
  >({
    url: `${baseUrl}/${id}`,
    method: "PATCH",
    schema: PorcentajeObraEditPayloadSchema,
    options: {
      onSuccess: (rawUpdated) => {
        const updatedItem = rawUpdated as LiquidacionEdificacionesListItem;
        // List cache is keyed by [prefix, page, page_size, filtros]; the exact
        // key is unknown here, so invalidate the prefix to refetch all variants.
        queryClient.invalidateQueries({ queryKey: LIST_KEY });
        // Sync into detail cache
        queryClient.setQueryData(
          ["liquidaciones", "edificaciones", "detalle", id],
          updatedItem,
        );
      },
    },
  });

  const editar = useMemo(
    () => ({
      ...mutation,
      mutate: (
        data: EdificacionesFormData,
        canEditProyecto: boolean = true,
      ) => {
        mutation.mutate(buildPayload(data, canEditProyecto));
      },
      mutateAsync: async (
        data: EdificacionesFormData,
        canEditProyecto: boolean = true,
      ) => {
        return mutation.mutateAsync(buildPayload(data, canEditProyecto));
      },
    }),
    [mutation],
  );

  return editar;
}
