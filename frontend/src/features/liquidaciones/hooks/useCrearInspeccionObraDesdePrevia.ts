/**
 * Hook para crear una Inspección de Obra PRIMERA-REVISIÓN desde una liquidación previa.
 * Usa useApiCreate genérico del proyecto.
 *
 * Endpoint: POST /liquidaciones/inspeccion-obra/nueva-liquidacion/primera-revision-desde-previa
 * Payload:
 * {
 *   liquidacion_previa_id: uuid,
 *   liquidacion_especifica: {
 *     datos: { cantidad_visitas: number, categoria: string },
 *     tarifa: { tarifa_visitas_id: string },
 *     inspector_id: string,
 *   }
 * }
 * Se hereda de la previa: proyecto, municipalidad, entidad, expediente, observacion, retencion.
 */
import { useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { useApiCreate } from "@/hooks";
import type { NuevaRevisionInspeccionObraFormData } from "../schemas/liquidacion-nueva-revision-io.schema";

const BASE_URL = "/liquidaciones/inspeccion-obra";

export function useCrearInspeccionObraDesdePrevia() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<
    unknown,
    {
      liquidacion_previa_id: string;
      liquidacion_especifica: {
        datos: { cantidad_visitas: number; categoria: string };
        tarifa: { tarifa_visitas_id: string };
        inspector_id: string;
      };
    }
  >({
    url: `${BASE_URL}/nueva-liquidacion/primera-revision-desde-previa`,
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

  // Wrapper que formatea el payload para la API
  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (payload: NuevaRevisionInspeccionObraFormData) => {
        mutation.mutate({
          liquidacion_previa_id: payload.liquidacion_previa_id,
          liquidacion_especifica: {
            datos: {
              cantidad_visitas: payload.cantidad_visitas,
              categoria: payload.categoria,
            },
            tarifa: { tarifa_visitas_id: payload.tarifa_visitas_id },
            inspector_id: payload.inspector_id,
          },
        });
      },
      mutateAsync: async (payload: NuevaRevisionInspeccionObraFormData) => {
        return mutation.mutateAsync({
          liquidacion_previa_id: payload.liquidacion_previa_id,
          liquidacion_especifica: {
            datos: {
              cantidad_visitas: payload.cantidad_visitas,
              categoria: payload.categoria,
            },
            tarifa: { tarifa_visitas_id: payload.tarifa_visitas_id },
            inspector_id: payload.inspector_id,
          },
        });
      },
    }),
    [mutation],
  );

  return crearMutation;
}
