/**
 * Hook para crear liquidaciones de Inspección de Obra (primera revisión).
 * Usa useApiCreate genérico del proyecto.
 *
 * Endpoint: POST /liquidaciones/inspeccion-obra/primera-revision
 */
import { useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { useApiCreate } from "@/hooks";
import type { VisitasFormData } from "../schemas/liquidacion-visitas-form.schema";

const BASE_URL = "/liquidaciones/inspeccion-obra";

export function useCrearInspeccionObra() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<unknown, { liquidacion_general: unknown; liquidacion_especifica: unknown }>({
    url: `${BASE_URL}/primera-revision`,
    options: {
      onSuccess: (created) => {
        const newItem = (created as { data?: unknown })?.data ?? created;
        queryClient.setQueriesData<{ items: unknown[]; total: number }>(
          { queryKey: ["liquidaciones", "inspeccion-obra"] },
          (old) => {
            if (!old || !Array.isArray(old.items)) return old;
            return {
              ...old,
              items: [newItem, ...old.items],
              total: (old.total ?? 0) + 1,
            };
          },
        );
      },
    },
  });

  // Wrapper that formats payload as { liquidacion_general, liquidacion_especifica } for the API
  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (payload: VisitasFormData) => {
        const { tarifa_visitas_id, cantidad_visitas, categoria, ...rest } = payload;
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
              cantidad_visitas,
              categoria,
            },
            tarifas: tarifa_visitas_id ? [{ tarifa_visitas_id }] : [],
          },
        });
      },
      mutateAsync: async (payload: VisitasFormData) => {
        const { tarifa_visitas_id, cantidad_visitas, categoria, ...rest } = payload;
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
              cantidad_visitas,
              categoria,
            },
            tarifas: tarifa_visitas_id ? [{ tarifa_visitas_id }] : [],
          },
        });
      },
    }),
    [mutation],
  );

  return crearMutation;
}
