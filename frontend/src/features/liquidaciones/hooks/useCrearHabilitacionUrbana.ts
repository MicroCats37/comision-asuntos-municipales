/**
 * Hook para crear liquidaciones de Habilitación Urbana (primera revisión).
 * Usa useApiCreate genérico del proyecto.
 *
 * Endpoint: POST /liquidaciones/habilitacion-urbana/primera-revision
 */
import { useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { useApiCreate } from "@/hooks";
import type { M2FormData } from "../schemas/liquidacion-m2-form.schema";

const BASE_URL = "/liquidaciones/habilitacion-urbana";

export function useCrearHabilitacionUrbana() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<unknown, { liquidacion_general: unknown; liquidacion_especifica: unknown }>({
    url: `${BASE_URL}/primera-revision`,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["liquidaciones", "habilitacion-urbana"] });
      },
    },
  });

  // Wrapper that formats payload as { liquidacion_general, liquidacion_especifica } for the API
  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (payload: M2FormData) => {
        const { tarifa_m2_id, area_solicitada, ...rest } = payload;
        mutation.mutate({
          liquidacion_general: {
            municipalidad_id: rest.municipalidad_id,
            expediente: rest.expediente,
            observacion: rest.observacion,
            proyecto: {
              denominacion: rest.denominacion,
              nombre_propietario: rest.nombre_propietario,
              direccion: rest.direccion,
              distrito_id: rest.distrito_id,
              entidad: {
                tipo_documento: rest.entidad_tipo_documento,
                numero_documento: rest.entidad_numero_documento,
                razon_social: rest.entidad_razon_social,
              },
            },
          },
          liquidacion_especifica: {
            datos: {
              area_solicitada,
            },
            tarifas: tarifa_m2_id ? [{ tarifa_m2_id }] : [],
          },
        });
      },
      mutateAsync: async (payload: M2FormData) => {
        const { tarifa_m2_id, area_solicitada, ...rest } = payload;
        return mutation.mutateAsync({
          liquidacion_general: {
            municipalidad_id: rest.municipalidad_id,
            expediente: rest.expediente,
            observacion: rest.observacion,
            proyecto: {
              denominacion: rest.denominacion,
              nombre_propietario: rest.nombre_propietario,
              direccion: rest.direccion,
              distrito_id: rest.distrito_id,
              entidad: {
                tipo_documento: rest.entidad_tipo_documento,
                numero_documento: rest.entidad_numero_documento,
                razon_social: rest.entidad_razon_social,
              },
            },
          },
          liquidacion_especifica: {
            datos: {
              area_solicitada,
            },
            tarifas: tarifa_m2_id ? [{ tarifa_m2_id }] : [],
          },
        });
      },
    }),
    [mutation],
  );

  return crearMutation;
}
