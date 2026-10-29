/**
 * Hook para crear RELACIONADA de Mecánica de Suelos (M2).
 *
 * POST /liquidaciones/mecanica-suelos/relacionada
 *
 * Usa useLiquidacionesCreateMutation (cache manual reactivo). La liquidación devuelta se inserta/actualiza en las listas visibles; la revisión previa permanece en la lista (ya no hay revisión canónica).
 */
import { useMemo } from "react";
import type { MecanicaSuelosFormData } from "../schemas/liquidacion-mecanica-suelos-form.schema";
import { useLiquidacionesCreateMutation } from "./cache";

const BASE_URL = "/liquidaciones/mecanica-suelos";
const LIST_KEY = ["liquidaciones", "mecanica-suelos"] as const;

/**
 * Payload de liquidación relacionada de Mecánica de Suelos.
 *
 * `numero_revision` viaja en el TOP LEVEL del body (contrato backend
 * `LiquidacionMecanicaSuelosRelacionadaInput` =
 * `NumeroRevisionRequeridoMixin` + wrappers): es obligatorio y lo elige el
 * usuario (etiqueta editable).
 */
export function buildCrearRelacionadaMecanicaSuelosPayload(
  data: MecanicaSuelosFormData,
  liquidacionPreviaId: string,
) {
  const { tarifa_m2_id, area_solicitada, numero_revision, ...rest } = data;
  return {
    liquidacion_previa_id: liquidacionPreviaId,
    numero_revision,
    liquidacion_general: {
      municipalidad_id: rest.municipalidad_id,
      expediente: rest.expediente,
      observacion: rest.observacion,
      denominacion_de_proyecto: rest.denominacion || undefined,
      proyecto: {
        nombre_propietario: rest.nombre_propietario,
        direccion: rest.direccion,
        distrito_id: rest.distrito_id || undefined,
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

export function useCrearRelacionadaMecanicaSuelos() {
  const mutation = useLiquidacionesCreateMutation<{
    liquidacion_general: unknown;
    liquidacion_especifica: unknown;
    liquidacion_previa_id: string;
    numero_revision: number;
  }>({
    tipoQueryKey: LIST_KEY,
    url: `${BASE_URL}/relacionada`,
  });

  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (data: MecanicaSuelosFormData, liquidacionPreviaId: string) => {
        mutation.mutate(
          buildCrearRelacionadaMecanicaSuelosPayload(
            data,
            liquidacionPreviaId,
          ),
        );
      },
      mutateAsync: async (
        data: MecanicaSuelosFormData,
        liquidacionPreviaId: string,
      ) => {
        return mutation.mutateAsync(
          buildCrearRelacionadaMecanicaSuelosPayload(
            data,
            liquidacionPreviaId,
          ),
        );
      },
    }),
    [mutation],
  );

  return crearMutation;
}
