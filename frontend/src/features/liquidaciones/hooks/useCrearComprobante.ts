/**
 * Hook para crear/reemplazar un comprobante en una LiquidacionGeneral.
 *
 * Endpoint: POST /liquidaciones/generales/{liquidacionId}/comprobante
 * Response: ApiResponse<LiquidacionGeneralOutput> — el data contiene la liquidacion
 * actualizada con comprobantes[] ya mutado en backend.
 *
 * Cache patch strategy (política híbrida — `useComprobanteCacheSync`):
 * - Detalle ['liquidaciones', 'generales', 'detalle', liquidacionId]: se MERGEa
 *   la liquidación devuelta dentro de `data.liquidacion_general`, conservando
 *   `liquidacion_especifica` y `liquidacion_tipo` del envelope cacheado.
 * - Listas ['liquidaciones', …]: se MERGEa la liquidación devuelta dentro de
 *   `data.items[i].liquidacion_general` (el item es un wrapper), sin alterar
 *   `total` ni la posición de los items.
 *
 * El browse RH NO se parchea (su clave `["rh-browse", …]` queda fuera del
 * prefijo `["liquidaciones"]`): ese hace `refetch()` explícito.
 *
 * No hay namespace de cache "ultimas-revisiones": ese endpoint fue retirado
 * del backend y no existe una revisión canónica por proyecto.
 *
 * No faz parte del modal UI (Phase D).
 */
import { useMutation } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import { handleApiError, notify } from "@/errors";
import api from "@/lib/api";
import { buildApiPayload } from "@/utils";
import type {
  CrearComprobanteInput,
  LiquidacionGeneralOutput,
} from "../schemas/liquidacion-base.schema";
import { useComprobanteCacheSync } from "./cache/useComprobanteCacheSync";

interface UseCrearComprobanteProps {
  /** ID de la liquidacion a la que se agrega el comprobante */
  liquidacionId: string;
  /** Called on success with the updated LiquidacionGeneralOutput */
  onSuccess?: (data: LiquidacionGeneralOutput) => void;
}

const BASE_URL = "/liquidaciones/generales";

export function useCrearComprobante({
  liquidacionId,
  onSuccess,
}: UseCrearComprobanteProps) {
  const cacheSync = useComprobanteCacheSync();

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
        // The envelope must be normalized as an HTTP payload (not as a bare
        // error object) so `error.message` AND `error.details` survive.
        throw Object.assign(
          new Error("La API no devolvió los datos esperados."),
          {
            response: { data, status: 200 },
          },
        );
      }
      return data.data as LiquidacionGeneralOutput;
    },
    onSuccess: (updatedLiquidacion) => {
      // ── 1. Parche de caché (detalle + listas) ─────────────────────────────
      // Política híbrida compartida con `useEditarComprobante`: el POST y el
      // PATCH dejan EXACTAMENTE la misma forma en caché.
      cacheSync.syncComprobante(liquidacionId, updatedLiquidacion);

      // ── 2. Sin invalidate de "ultimas-revisiones" ─────────────────────────
      // Ese namespace de cache ya no existe: el backend retiró el endpoint
      // `GET /liquidaciones/generales/ultimas-revisiones` y el modelo de datos
      // no tiene una revisión canónica por proyecto. El listado general es el
      // paginado completo y ya fue parcheado arriba.

      onSuccess?.(updatedLiquidacion);
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      notify.error(apiError.message);
    },
  });
}
