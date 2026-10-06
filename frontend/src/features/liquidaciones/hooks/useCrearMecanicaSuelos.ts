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

export function useCrearMecanicaSuelos() {
  const mutation = useLiquidacionesCreateMutation<{
    liquidacion_general: unknown;
    liquidacion_especifica: unknown;
  }>({
    tipoQueryKey: LIST_KEY,
    url: `${BASE_URL}/nueva-liquidacion/primera-revision`,
  });

  // Wrapper that formats payload as { liquidacion_general, liquidacion_especifica } for the API
  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (payload: MecanicaSuelosFormData) => {
        const { tarifa_m2_id, area_solicitada, ...rest } = payload;
        mutation.mutate({
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
            // Contacto principal (singular, opcional)
            ...(rest.contacto ? { contacto: rest.contacto } : {}),
          },
          liquidacion_especifica: {
            datos: {
              area_solicitada,
            },
            tarifa: tarifa_m2_id ? { tarifa_m2_id } : { tarifa_m2_id: "" },
          },
        });
      },
      mutateAsync: async (payload: MecanicaSuelosFormData) => {
        const { tarifa_m2_id, area_solicitada, ...rest } = payload;
        return mutation.mutateAsync({
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
            // Contacto principal (singular, opcional)
            ...(rest.contacto ? { contacto: rest.contacto } : {}),
          },
          liquidacion_especifica: {
            datos: {
              area_solicitada,
            },
            tarifa: tarifa_m2_id ? { tarifa_m2_id } : { tarifa_m2_id: "" },
          },
        });
      },
    }),
    [mutation],
  );

  return crearMutation;
}
