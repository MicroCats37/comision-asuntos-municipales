/**
 * useQuitarDelegadoLiquidacion
 *
 * Quita (desasigna) UN delegado de una liquidación.
 *
 * Endpoint: PATCH /liquidaciones/{liquidacion_id}/delegados
 * Payload:   { delete: [{ delegado_id }] }   ← un único item: UN PATCH por fila.
 *
 * Reusa el contrato batch EXISTENTE: no hay endpoint nuevo, ni presenter, ni
 * payload nuevo. El payload se construye DENTRO del hook (el componente nunca
 * lo arma), tal como exige el contrato de arquitectura de Next.js.
 *
 * Granularidad: una fila por request. El batch del backend es atómico, así que
 * un único 409 en un batch multi-fila abortaría el resto de las filas y el
 * operador no podría saber cuáles sí procedían.
 *
 * El rechazo 409 (RH mensual enlazado) NO invalida nada: la mutación falla,
 * el backend no toca la base de datos y el estado del servidor no cambia.
 *
 * Al tener éxito invalida el detalle de ASIGNACIONES (la fila quitada no debe
 * reaparecer al reabrir el modal dedicado), el detalle de la liquidación, las
  * listas visibles, el listado del browse de RH y las candidatas de RH mensual.
  * Así, una liquidación desasignada vuelve a estar disponible para seleccionarla
  * en el flujo de RH mensual.
 */

import { useQueryClient } from "@tanstack/react-query";
import { useApiUpdate } from "@/hooks/callsApi/useApiUpdate";
import {
  type LiquidacionDelegadoBatchResponse,
  LiquidacionDelegadoBatchResponseSchema,
} from "../schemas/liquidacion-delegado-batch.schema";
import {
  GENERALES_KEY_PREFIX,
  GENERALES_TODAS_SUFFIX,
  TIPO_KEY_PREFIXES,
} from "./cache";

/** Payload que viaja al backend — un único item en la rama `delete`. */
export type QuitarDelegadoPayload = {
  delete: { delegado_id: string }[];
};

/** Variables de la mutación: lo que el componente declara (una sola fila). */
export type QuitarDelegadoVariables = {
  delegado_id: string;
};

interface UseQuitarDelegadoLiquidacionOptions {
  /**
   * Endpoint activo del browse de RH (p. ej. "/liquidaciones/generales/").
   *
   * Se invalida como `["rh-browse", "liquidaciones", endpoint]` porque la
   * tarjeta del browse puede llevar el dato removido. Es OPCIONAL: las vistas
   * por tipo (que usan `GestionarDelegadosModal`) no viven en el browse y no
   * necesitan invalidarlo.
   */
  rhBrowseEndpoint?: string | null;
}

export function useQuitarDelegadoLiquidacion(
  liquidacionId: string,
  { rhBrowseEndpoint }: UseQuitarDelegadoLiquidacionOptions = {},
) {
  const queryClient = useQueryClient();

  const mutation = useApiUpdate<
    LiquidacionDelegadoBatchResponse,
    QuitarDelegadoPayload
  >({
    url: `/liquidaciones/${liquidacionId}/delegados`,
    method: "PATCH",
    schema: LiquidacionDelegadoBatchResponseSchema,
    options: {
      onSuccess: () => {
        // 1) Detalle de ASIGNACIONES — la fila quitada no debe reaparecer al
        //    reabrir el modal dedicado.
        queryClient.invalidateQueries({
          queryKey: ["liquidaciones", "delegados-asignaciones", liquidacionId],
        });
        // 2) Detalle de la liquidación — el delegado quitado ya no debe aparecer.
        queryClient.invalidateQueries({
          queryKey: ["liquidaciones", "generales", "detalle", liquidacionId],
        });
        // 3) Listado general visible ("todas").
        queryClient.invalidateQueries({
          queryKey: [...GENERALES_KEY_PREFIX, GENERALES_TODAS_SUFFIX],
        });
        // 4) Listados tipo-específicos visibles (edificaciones, HU, MS, ...).
        for (const tipoPrefijo of TIPO_KEY_PREFIXES) {
          queryClient.invalidateQueries({ queryKey: [...tipoPrefijo] });
        }
        // 5) Candidatas del RH mensual: la liquidación vuelve a ser elegible.
        queryClient.invalidateQueries({
          queryKey: ["delegados", "candidatas"],
        });
        // 6) Listado del browse de RH (la tarjeta puede llevar el dato quitado).
        if (rhBrowseEndpoint) {
          queryClient.invalidateQueries({
            queryKey: ["rh-browse", "liquidaciones", rhBrowseEndpoint],
          });
        }
      },
    },
  });

  return {
    ...mutation,
    /**
     * Quita UN delegado: emite exactamente un PATCH con un array `delete` de un
     * único elemento. Rechaza si el backend responde 409 (el mensaje lo arma
     * el componente con `handleApiError(error).message`).
     */
    quitar: (variables: QuitarDelegadoVariables) =>
      mutation.mutateAsync({ delete: [variables] }),
  };
}
