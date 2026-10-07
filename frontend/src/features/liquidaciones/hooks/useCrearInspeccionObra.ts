/**
 * Hook para crear liquidaciones de Inspección de Obra (primera revisión).
 * Usa useLiquidacionesCreateMutation (cache manual reactivo) + useApiCreate interno.
 *
 * Endpoint: POST /liquidaciones/inspeccion-obra/nueva-liquidacion
 */
import { useMemo } from "react";
import type { VisitasFormData } from "../schemas/liquidacion-visitas-form.schema";
import { useLiquidacionesCreateMutation } from "./cache";

const BASE_URL = "/liquidaciones/inspeccion-obra";
const LIST_KEY = ["liquidaciones", "inspeccion-obra"] as const;

export function useCrearInspeccionObra() {
  const mutation = useLiquidacionesCreateMutation<{
    liquidacion_general: unknown;
    liquidacion_especifica: {
      datos: { cantidad_visitas: number; categoria: string };
      tarifa: { tarifa_visitas_id: string | undefined };
      inspector_id: string | undefined;
    };
  }>({
    tipoQueryKey: LIST_KEY,
    url: `${BASE_URL}/nueva-liquidacion`,
  });

  // Wrapper that formats payload as { liquidacion_general, liquidacion_especifica } for the API.
  // tipo_liquidacion_id is NOT sent — it's only used in the frontend to filter the inspector modal.
  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (payload: VisitasFormData) => {
        const { tarifa_visitas_id, cantidad_visitas, categoria, ...rest } =
          payload;
        mutation.mutate({
          liquidacion_general: {
            municipalidad_id: rest.municipalidad_id,
            expediente: rest.expediente,
            observacion: rest.observacion,
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
              cantidad_visitas,
              categoria,
            },
            tarifa: { tarifa_visitas_id },
            inspector_id: rest.inspector_id,
          },
        });
      },
      mutateAsync: async (payload: VisitasFormData) => {
        const { tarifa_visitas_id, cantidad_visitas, categoria, ...rest } =
          payload;
        return mutation.mutateAsync({
          liquidacion_general: {
            municipalidad_id: rest.municipalidad_id,
            expediente: rest.expediente,
            observacion: rest.observacion,
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
              cantidad_visitas,
              categoria,
            },
            tarifa: { tarifa_visitas_id },
            inspector_id: rest.inspector_id,
          },
        });
      },
    }),
    [mutation],
  );

  return crearMutation;
}
