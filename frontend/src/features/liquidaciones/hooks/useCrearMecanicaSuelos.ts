/**
 * Hook para crear liquidaciones de Mecánica de Suelos (primera revisión).
 * Usa useLiquidacionesCreateMutation (cache manual reactivo) + useApiCreate interno.
 *
 * Endpoint: POST /liquidaciones/mecanica-suelos/nueva-liquidacion/primera-revision
 * Payload M2: liquidacion_especifica { datos: { area_solicitada }, tarifa: { tarifa_m2_id } }
 */
import { useMemo } from "react";
import type { MecanicaSuelosFormData } from "../schemas/liquidacion-mecanica-suelos-form.schema";
import { useLiquidacionesCreateMutation } from "./cache";

const BASE_URL = "/liquidaciones/mecanica-suelos";
const LIST_KEY = ["liquidaciones", "mecanica-suelos"] as const;

/**
 * Payload de creación (primera-revisión) de Mecánica de Suelos.
 *
 * `numero_revision` viaja en el TOP LEVEL del body (contrato backend
 * `LiquidacionMecanicaSuelosInput` = `NumeroRevisionRequeridoMixin` +
 * wrappers): es obligatorio y lo elige el usuario.
 */
export function buildCrearMecanicaSuelosPayload(
  payload: MecanicaSuelosFormData,
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

export function useCrearMecanicaSuelos() {
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
      mutate: (payload: MecanicaSuelosFormData) => {
        mutation.mutate(buildCrearMecanicaSuelosPayload(payload));
      },
      mutateAsync: async (payload: MecanicaSuelosFormData) => {
        return mutation.mutateAsync(buildCrearMecanicaSuelosPayload(payload));
      },
    }),
    [mutation],
  );

  return crearMutation;
}
