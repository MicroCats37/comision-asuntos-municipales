/**
 * Hook para crear liquidaciones de Habilitación Urbana (primera revisión).
 * Usa useLiquidacionesCreateMutation (cache manual reactivo) + useApiCreate interno.
 *
 * Endpoint: POST /liquidaciones/habilitacion-urbana/nueva-liquidacion/primera-revision
 * Payload M2: liquidacion_especifica { datos: { area_solicitada }, tarifa: { tarifa_m2_id } }
 */
import { useMemo } from "react";
import type { HabilitacionUrbanaFormData } from "../schemas/liquidacion-habilitacion-urbana-form.schema";
import { useLiquidacionesCreateMutation } from "./cache";

const BASE_URL = "/liquidaciones/habilitacion-urbana";
const LIST_KEY = ["liquidaciones", "habilitacion-urbana"] as const;

/**
 * Payload de creación (primera-revisión) de Habilitación Urbana.
 *
 * `numero_revision` viaja en el TOP LEVEL del body (contrato backend
 * `LiquidacionHabilitacionUrbanaInput` = `NumeroRevisionRequeridoMixin` +
 * wrappers): es obligatorio y lo elige el usuario.
 */
export function buildCrearHabilitacionUrbanaPayload(
  payload: HabilitacionUrbanaFormData,
) {
  const { tarifa_m2_id, area_solicitada, numero_revision, ...rest } = payload;
  return {
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
      // Contacto principal (singular, opcional)
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

export function useCrearHabilitacionUrbana() {
  const mutation = useLiquidacionesCreateMutation<{
    liquidacion_general: unknown;
    liquidacion_especifica: unknown;
    numero_revision: number;
  }>({
    tipoQueryKey: LIST_KEY,
    url: `${BASE_URL}/nueva-liquidacion/primera-revision`,
  });

  // Wrapper that formats payload as { liquidacion_general, liquidacion_especifica } for the API
  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (payload: HabilitacionUrbanaFormData) => {
        mutation.mutate(buildCrearHabilitacionUrbanaPayload(payload));
      },
      mutateAsync: async (payload: HabilitacionUrbanaFormData) => {
        return mutation.mutateAsync(
          buildCrearHabilitacionUrbanaPayload(payload),
        );
      },
    }),
    [mutation],
  );

  return crearMutation;
}
