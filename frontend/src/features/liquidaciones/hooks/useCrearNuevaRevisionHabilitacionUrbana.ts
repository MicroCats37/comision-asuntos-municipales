/**
 * Hook para crear NUEVA REVISIÓN de Habilitación Urbana (M2).
 *
 * POST /liquidaciones/habilitacion-urbana/nueva-revision
 * Payload:
 * {
 *   liquidacion_previa_id: uuid,
 *   liquidacion_general: { municipalidad_id, expediente, denominacion_de_proyecto, ...proyecto, contacto? },
 *   liquidacion_especifica: { datos: { area_solicitada }, tarifa: { tarifa_m2_id } }
 * }
 *
 * M2 usa `area_solicitada` (no `valor_declarado`) y `tarifa_m2_id` singular (no array de especialidades).
 *
 * Usa useLiquidacionesCreateMutation (cache manual reactivo). La liquidación devuelta se inserta/actualiza en las listas visibles; la revisión previa permanece en la lista (ya no hay revisión canónica).
 */
import { useMemo } from "react";
import type { HabilitacionUrbanaFormData } from "../schemas/liquidacion-habilitacion-urbana-form.schema";
import { useLiquidacionesCreateMutation } from "./cache";

const BASE_URL = "/liquidaciones/habilitacion-urbana";
const LIST_KEY = ["liquidaciones", "habilitacion-urbana"] as const;

/**
 * Payload de nueva revisión de Habilitación Urbana.
 *
 * `numero_revision` viaja en el TOP LEVEL del body (contrato backend
 * `LiquidacionHabilitacionUrbanaNuevaRevisionInput` =
 * `NumeroRevisionRequeridoMixin` + wrappers): es obligatorio y lo elige el
 * usuario (etiqueta editable).
 */
export function buildCrearNuevaRevisionHabilitacionUrbanaPayload(
  data: HabilitacionUrbanaFormData,
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

export function useCrearNuevaRevisionHabilitacionUrbana() {
  const mutation = useLiquidacionesCreateMutation<{
    liquidacion_general: unknown;
    liquidacion_especifica: unknown;
    liquidacion_previa_id: string;
    numero_revision: number;
  }>({
    tipoQueryKey: LIST_KEY,
    url: `${BASE_URL}/nueva-revision`,
  });

  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (
        data: HabilitacionUrbanaFormData,
        liquidacionPreviaId: string,
      ) => {
        mutation.mutate(
          buildCrearNuevaRevisionHabilitacionUrbanaPayload(
            data,
            liquidacionPreviaId,
          ),
        );
      },
      mutateAsync: async (
        data: HabilitacionUrbanaFormData,
        liquidacionPreviaId: string,
      ) => {
        return mutation.mutateAsync(
          buildCrearNuevaRevisionHabilitacionUrbanaPayload(
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
