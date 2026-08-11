/**
 * Hook para crear liquidaciones de Edificaciones (primera revisión).
 * Usa useApiCreate genérico del proyecto.
 *
 * Endpoint: POST /liquidaciones/edificaciones/nueva-liquidacion/primera-revision
 */
import { useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { useApiCreate } from "@/hooks";
import type { EdificacionesFormData } from "../schemas/liquidacion-edificaciones-form.schema";
import { liquidacionEdificacionOutSchema } from "../types/liquidacion-edificaciones.types";

const BASE_URL = "/liquidaciones/edificaciones/nueva-liquidacion";

export function useCrearEdificaciones() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<unknown, { liquidacion_general: unknown; liquidacion_especifica: unknown }>({
    url: `${BASE_URL}/primera-revision`,
    options: {
      onSuccess: (created) => {
        // The POST returns ApiResponse envelope: { success, data: { liquidacion_general, ... }, error }
        // Unwrap to get the list item shape and prepend to cache
        const newItem = (created as { data?: unknown })?.data ?? created;
        queryClient.setQueriesData<{ items: unknown[]; total: number }>(
          { queryKey: ["liquidaciones", "edificaciones"] },
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
      mutate: (payload: EdificacionesFormData) => {
        const { tarifas_ids, ...rest } = payload;
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
              valor_declarado: rest.valor_declarado,
            },
            tarifas: (tarifas_ids || []).map((id) => ({
              tarifa_porcentaje_obra_id: id,
            })),
          },
        });
      },
      mutateAsync: async (payload: EdificacionesFormData) => {
        const { tarifas_ids, ...rest } = payload;
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
              valor_declarado: rest.valor_declarado,
            },
            tarifas: (tarifas_ids || []).map((id) => ({
              tarifa_porcentaje_obra_id: id,
            })),
          },
        });
      },
    }),
    [mutation],
  );

  return crearMutation;
}
