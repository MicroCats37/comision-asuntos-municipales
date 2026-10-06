/**
 * Hook para crear una liquidación RELACIONADA de Inspección de Obra.
 *
 * POST /liquidaciones/inspeccion-obra/relacionada
 * Payload:
 * {
 *   liquidacion_previa_id: uuid,
 *   liquidacion_especifica: {
 *     datos: { cantidad_visitas: number, categoria: string },
 *     tarifa: { tarifa_visitas_id: string },
 *     inspector_id: string,
 *   },
 *   contacto?: { nombres, apellidos, dni, cargo, telefono, celular, email },
 * }
 *
 * Crea una liquidación con numero_revision = 1, heredando proyecto, municipalidad,
 * entidad, expediente, observacion, retencion de la previa.
 *
 * Usa useLiquidacionesCreateMutation (cache manual reactivo) con lógica de ultimas-revisiones.
 */
import { useMemo, useRef } from "react";
import type { NuevaRevisionInspeccionObraFormData } from "../schemas/liquidacion-nueva-revision-io.schema";
import type { LiquidacionWrapper } from "./cache";
import {
  useLiquidacionesCacheUtils,
  useLiquidacionesCreateMutation,
} from "./cache";

const BASE_URL = "/liquidaciones/inspeccion-obra";
const LIST_KEY = ["liquidaciones", "inspeccion-obra"] as const;
const TIPO_KEY = "inspeccion-obra";

export function useCrearRelacionadaInspeccionObra() {
  const previousIdRef = useRef<string | null>(null);
  const cacheUtils = useLiquidacionesCacheUtils();

  const mutation = useLiquidacionesCreateMutation<{
    liquidacion_previa_id: string;
    liquidacion_especifica: {
      datos: { cantidad_visitas: number; categoria: string };
      tarifa: { tarifa_visitas_id: string };
      inspector_id: string;
    };
    contacto?: {
      nombres: string;
      apellidos?: string;
      dni?: string;
      cargo?: string;
      telefono?: string;
      celular?: string;
      email?: string;
    };
  }>({
    tipoQueryKey: LIST_KEY,
    url: `${BASE_URL}/relacionada`,
    options: {
      onSuccess: (rawResult) => {
        const response = rawResult as { data?: LiquidacionWrapper };
        const newItem: LiquidacionWrapper =
          response?.data ?? (rawResult as LiquidacionWrapper);
        if (!newItem?.liquidacion_general?.id) return;

        cacheUtils.insertCreatedItem(newItem, { tipoKey: TIPO_KEY });

        const prevId = previousIdRef.current;
        if (prevId) {
          cacheUtils.replaceLatestRevision(newItem, {
            tipoKey: TIPO_KEY,
            previousId: prevId,
          });
        }
      },
    },
  });

  const buildPayload = (payload: NuevaRevisionInspeccionObraFormData) => ({
    liquidacion_previa_id: payload.liquidacion_previa_id,
    liquidacion_especifica: {
      datos: {
        cantidad_visitas: payload.cantidad_visitas,
        categoria: payload.categoria,
      },
      tarifa: { tarifa_visitas_id: payload.tarifa_visitas_id },
      inspector_id: payload.inspector_id,
    },
    contacto: payload.contacto ?? undefined,
  });

  // biome-ignore lint/correctness/useExhaustiveDependencies: buildPayload is stable
  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (payload: NuevaRevisionInspeccionObraFormData) => {
        previousIdRef.current = payload.liquidacion_previa_id;
        mutation.mutate(buildPayload(payload));
      },
      mutateAsync: async (payload: NuevaRevisionInspeccionObraFormData) => {
        previousIdRef.current = payload.liquidacion_previa_id;
        return mutation.mutateAsync(buildPayload(payload));
      },
    }),
    [mutation],
  );

  return crearMutation;
}
