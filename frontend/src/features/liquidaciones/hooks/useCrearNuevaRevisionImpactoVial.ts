/**
 * Hook para crear NUEVA REVISIÓN de Impacto Vial.
 *
 * POST /liquidaciones/impacto-vial/nueva-revision
 * Payload: { liquidacion_previa_id, liquidacion_general, liquidacion_especifica }
 *
 * Usa useLiquidacionesCreateMutation (cache manual reactivo) con lógica de ultimas-revisiones.
 */
import { useMemo, useRef } from "react";
import type { ImpactoVialFormData } from "../schemas/liquidacion-impacto-vial-form.schema";
import type { LiquidacionWrapper } from "./cache";
import {
  useLiquidacionesCacheUtils,
  useLiquidacionesCreateMutation,
} from "./cache";

const BASE_URL = "/liquidaciones/impacto-vial";
const LIST_KEY = ["liquidaciones", "impacto-vial"] as const;
const TIPO_KEY = "impacto-vial";

function buildPayload(data: ImpactoVialFormData, liquidacionPreviaId: string) {
  const { tarifa_unica_id, especialidades_seleccionadas, ...rest } = data;
  const espIds = especialidades_seleccionadas ?? [];
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
        valor_declarado: rest.valor_declarado,
      },
      tarifas: espIds.map((espId) => ({
        tarifa_porcentaje_obra_id: tarifa_unica_id as string,
        especialidad_id: espId,
      })),
    },
  };
}

export function useCrearNuevaRevisionImpactoVial() {
  const previousIdRef = useRef<string | null>(null);
  const cacheUtils = useLiquidacionesCacheUtils();

  const mutation = useLiquidacionesCreateMutation<{
    liquidacion_general: unknown;
    liquidacion_especifica: unknown;
    liquidacion_previa_id: string;
  }>({
    tipoQueryKey: LIST_KEY,
    url: `${BASE_URL}/nueva-revision`,
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
      mutate: (data: ImpactoVialFormData, liquidacionPreviaId: string) => {
        previousIdRef.current = liquidacionPreviaId;
        mutation.mutate(buildPayload(data, liquidacionPreviaId));
      },
      mutateAsync: async (
        data: ImpactoVialFormData,
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
