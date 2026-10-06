/**
 * Hook para crear RELACIONADA de Habilitación Urbana (M2).
 *
 * POST /liquidaciones/habilitacion-urbana/relacionada
 * Payload: mismo shape que nueva-revision (area_solicitada + tarifa_m2_id).
 *
 * Usa useLiquidacionesCreateMutation (cache manual reactivo) con lógica de ultimas-revisiones.
 */
import { useMemo, useRef } from "react";
import type { HabilitacionUrbanaFormData } from "../schemas/liquidacion-habilitacion-urbana-form.schema";
import type { LiquidacionWrapper } from "./cache";
import {
  useLiquidacionesCacheUtils,
  useLiquidacionesCreateMutation,
} from "./cache";

const BASE_URL = "/liquidaciones/habilitacion-urbana";
const LIST_KEY = ["liquidaciones", "habilitacion-urbana"] as const;
const TIPO_KEY = "habilitacion-urbana";

function buildPayload(
  data: HabilitacionUrbanaFormData,
  liquidacionPreviaId: string,
) {
  const { tarifa_m2_id, area_solicitada, ...rest } = data;
  return {
    liquidacion_previa_id: liquidacionPreviaId,
    liquidacion_general: {
      municipalidad_id: rest.municipalidad_id,
      expediente: rest.expediente,
      observacion: rest.observacion,
      retencion: rest.retencion ?? false,
      denominacion_de_proyecto: rest.denominacion || undefined,
      proyecto: {
        nombre_propietario: rest.nombre_propietario,
        direccion: rest.direccion,
        distrito_id: rest.distrito_id,
        urbanizacion: rest.urbanizacion || undefined,
        entidad: {
          tipo_documento: rest.entidad_tipo_documento,
          numero_documento: rest.entidad_numero_documento,
          razon_social: rest.entidad_razon_social,
        },
      },
      ...(rest.contacto ? { contacto: rest.contacto } : {}),
    },
    liquidacion_especifica: {
      datos: {
        area_solicitada,
      },
      tarifa: tarifa_m2_id ? { tarifa_m2_id } : { tarifa_m2_id: "" },
    },
  };
}

export function useCrearRelacionadaHabilitacionUrbana() {
  const previousIdRef = useRef<string | null>(null);
  const cacheUtils = useLiquidacionesCacheUtils();

  const mutation = useLiquidacionesCreateMutation<{
    liquidacion_general: unknown;
    liquidacion_especifica: unknown;
    liquidacion_previa_id: string;
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

  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (
        data: HabilitacionUrbanaFormData,
        liquidacionPreviaId: string,
      ) => {
        previousIdRef.current = liquidacionPreviaId;
        mutation.mutate(buildPayload(data, liquidacionPreviaId));
      },
      mutateAsync: async (
        data: HabilitacionUrbanaFormData,
        liquidacionPreviaId: string,
      ) => {
        previousIdRef.current = liquidacionPreviaId;
        return mutation.mutateAsync(buildPayload(data, liquidacionPreviaId));
      },
    }),
    [mutation],
  );

  return crearMutation;
}
