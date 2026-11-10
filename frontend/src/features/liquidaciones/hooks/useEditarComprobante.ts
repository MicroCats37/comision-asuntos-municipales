/**
 * Hook para editar IN PLACE el comprobante ACTIVO de una LiquidacionGeneral.
 *
 * Endpoint: PATCH /liquidaciones/generales/{liquidacionId}/comprobante/{comprobanteId}
 * Response: ApiResponse<LiquidacionGeneralOutput> — el MISMO envelope que devuelve
 * `POST /liquidaciones/generales/{id}/comprobante`, de modo que el cliente cachea
 * el resultado sin conocer una forma de respuesta nueva.
 *
 * Contrato del cuerpo (espejo de `LiquidacionComprobanteUpdateIn` del backend):
 * `{ tipo_comprobante, serie?, numero?, fecha_emision? }`
 *
 * El payload se construye AQUÍ, nunca en el componente del formulario
 * (`next-app-architecture-contract.md` §5). En particular:
 * - `monto` NO forma parte del contrato de entrada: el backend lo preserva y el
 *   cliente no puede sobrescribirlo;
 * - los strings vacíos se descartan (el backend los convertiría a `null`).
 *
 * Cache patch strategy: idéntica a la de `useCrearComprobante` (política
 * híbrida compartida en `useComprobanteCacheSync`) para que ambas rutas
 * dejen la misma forma en la caché:
 * - Detalle ['liquidaciones', 'generales', 'detalle', liquidacionId]: se MERGEa
 *   la liquidación devuelta dentro de `data.liquidacion_general`, conservando
 *   `liquidacion_especifica` y `liquidacion_tipo` del envelope cacheado.
 * - Listas ['liquidaciones', …]: se MERGEa la liquidación devuelta dentro de
 *   `data.items[i].liquidacion_general` (el item es un wrapper), sin alterar
 *   `total` ni la posición de los items.
 */
import { useMutation } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import { handleApiError, notify } from "@/errors";
import api from "@/lib/api";
import { buildApiPayload } from "@/utils";
import type {
  EditarComprobanteInput,
  LiquidacionGeneralOutput,
} from "../schemas/liquidacion-base.schema";
import { useComprobanteCacheSync } from "./cache/useComprobanteCacheSync";

export interface UseEditarComprobanteProps {
  /** ID de la liquidacion a la que pertenece el comprobante */
  liquidacionId: string;
  /** ID del comprobante ACTIVO a editar in-place */
  comprobanteId: string;
  /** Called on success with the updated LiquidacionGeneralOutput */
  onSuccess?: (data: LiquidacionGeneralOutput) => void;
}

const BASE_URL = "/liquidaciones/generales";

/**
 * Traduce los valores del formulario al cuerpo del PATCH.
 *
 * - Descarta los strings vacíos (el usuario no rellenó el campo).
 * - NUNCA incluye `monto`: no existe en el contrato de entrada, así que el monto
 *   persistido se preserva por construcción, no por disciplina del cliente.
 * - NUNCA incluye `motivo_reemplazo`: el reemplazo es otra operación.
 */
function buildEditarComprobantePayload(input: EditarComprobanteInput) {
  return {
    tipo_comprobante: input.tipo_comprobante,
    serie: input.serie || undefined,
    numero: input.numero || undefined,
    fecha_emision: input.fecha_emision || undefined,
  };
}

export function useEditarComprobante({
  liquidacionId,
  comprobanteId,
  onSuccess,
}: UseEditarComprobanteProps) {
  const cacheSync = useComprobanteCacheSync();

  return useMutation<
    LiquidacionGeneralOutput,
    AxiosError,
    EditarComprobanteInput
  >({
    mutationFn: async (input) => {
      const payload = buildApiPayload(buildEditarComprobantePayload(input));
      const { data } = await api.patch(
        `${BASE_URL}/${liquidacionId}/comprobante/${comprobanteId}`,
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
      // Política híbrida compartida con `useCrearComprobante`: el POST y el
      // PATCH dejan EXACTAMENTE la misma forma en caché.
      cacheSync.syncComprobante(liquidacionId, updatedLiquidacion);

      // ── 2. Sin invalidate de "ultimas-revisiones" ─────────────────────────
      // Ese namespace de cache ya no existe: el backend retiró el endpoint
      // `GET /liquidaciones/generales/ultimas-revisiones`. La edición del
      // comprobante NO crea revisiones: `numero_revision` es invariante.

      onSuccess?.(updatedLiquidacion);
    },
    onError: (error) => {
      const apiError = handleApiError(error);
      notify.error(apiError.message);
    },
  });
}
