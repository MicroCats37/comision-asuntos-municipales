/**
 * Hook para crear/reemplazar un comprobante en una LiquidacionGeneral.
 *
 * Endpoint: POST /liquidaciones/generales/{liquidacionId}/comprobante
 * Response: ApiResponse<LiquidacionGeneralOutput> — el data contiene la liquidacion
 * actualizada con comprobantes[] ya mutado en backend.
 *
 * Cache patch strategy:
 * - Lista paginada ['liquidaciones', 'generales', 'todas', ...]: se busca y reemplaza
 *   el item con id matching usando setQueriesData con stale key filtering.
 * - Detalle ['liquidaciones', 'generales', 'detail', liquidacionId]: se reemplaza
 *   el item completo con los datos del response.
 * - Invalidate de ultimas-revisiones como fallback seguro.
 *
 * No faz parte del modal UI (Phase D).
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import { handleApiError, notify } from "@/errors";
import api from "@/lib/api";
import { buildApiPayload } from "@/utils";
import type { LiquidacionGeneralOutput } from "../schemas/liquidacion-base.schema";
import type { CrearComprobanteInput } from "../schemas/liquidacion-base.schema";

interface UseCrearComprobanteProps {
  /** ID de la liquidacion a la que se agrega el comprobante */
  liquidacionId: string;
  /** Called on success with the updated LiquidacionGeneralOutput */
  onSuccess?: (data: LiquidacionGeneralOutput) => void;
}

const BASE_URL = "/liquidaciones/generales";

/**
 * Builds the cache key prefix used by useLiquidacionesGenerales for the general list.
 * Must stay in sync with useLiquidacionesGenerales queryKey structure.
 */
function makeListQueryKeyPrefix(): [
  "liquidaciones",
  "generales",
  string,
  number,
  number,
] {
  // The base prefix without filters — setQueriesData matches by prefix.
  // useLiquidacionesGenerales builds: ['liquidaciones', 'generales', 'todas', page, pageSize, ...filters]
  return ["liquidaciones", "generales", "todas", 1, 10];
}

/**
 * Builds the detail cache key for a specific liquidacion.
 */
function makeDetailQueryKey(
  liquidacionId: string,
): [string, string, string, string] {
  return ["liquidaciones", "generales", "detail", liquidacionId];
}

export function useCrearComprobante({
  liquidacionId,
  onSuccess,
}: UseCrearComprobanteProps) {
  const queryClient = useQueryClient();

  return useMutation<
    LiquidacionGeneralOutput,
    AxiosError,
    CrearComprobanteInput
  >({
    mutationFn: async (input) => {
      const payload = buildApiPayload(input);
      const { data } = await api.post(
        `${BASE_URL}/${liquidacionId}/comprobante`,
        payload,
      );
      // Backend returns ApiResponse<LiquidacionGeneralOutput>: { success, data, error }
      // Unwrap the envelope
      if (!data.success || !data.data) {
        const apiError = handleApiError(data.error ?? new Error("API error"));
        notify.error(apiError.message);
        throw apiError;
      }
      return data.data as LiquidacionGeneralOutput;
    },
    onSuccess: (updatedLiquidacion) => {
      // ── 1. Patch detail cache ─────────────────────────────────────────────
      queryClient.setQueryData<LiquidacionGeneralOutput>(
        makeDetailQueryKey(liquidacionId),
        updatedLiquidacion,
      );

      // ── 2. Patch paginated list caches (all pages that may contain this item) ─
      // Use setQueriesData with predicate to replace matching items.
      // The prefix matches the list query keys from useLiquidacionesGenerales.
      const listPrefix = makeListQueryKeyPrefix();
      queryClient.setQueriesData<
        { items?: LiquidacionGeneralOutput[] } | undefined
      >(
        { queryKey: listPrefix },
        (old: { items?: LiquidacionGeneralOutput[] } | undefined) => {
          if (!old) return old;
          // Handle paginated shape: { items: T[], total, page, page_size, total_pages }
          if (Array.isArray(old.items)) {
            return {
              ...old,
              items: old.items.map((item: LiquidacionGeneralOutput) =>
                item.id === updatedLiquidacion.id ? updatedLiquidacion : item,
              ),
            };
          }
          return old;
        },
      );

      // ── 3. Invalidate ultimas-revisiones as safe fallback ─────────────────
      queryClient.invalidateQueries({
        queryKey: ["liquidaciones", "generales", "ultimas-revisiones"],
      });

      onSuccess?.(updatedLiquidacion);
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      notify.error(apiError.message);
    },
  });
}
