/**
 * Hook para crear NUEVA REVISIÓN de Edificaciones.
 * Usa useApiCreate genérico del proyecto.
 *
 * Endpoint: POST /liquidaciones/edificaciones/nueva-revision
 * Payload (schema propio reducido):
 * {
 *   liquidacion_previa_id: uuid,
 *   liquidacion_general: { expediente, observacion, retencion, contacto? },
 *   liquidacion_especifica: { tarifas: [{ tarifa_porcentaje_obra_id }] }
 * }
 * Se hereda de la previa: valor_declarado, municipalidad_id, proyecto.
 */
import { useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { useApiCreate } from "@/hooks";
import type { NuevaRevisionEdificacionesFormData } from "../schemas/liquidacion-nueva-revision-form.schema";

const BASE_URL = "/liquidaciones/edificaciones";

export function useCrearNuevaRevisionEdificaciones() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<unknown, { liquidacion_general: unknown; liquidacion_especifica: unknown; liquidacion_previa_id: string }>({
    url: `${BASE_URL}/nueva-revision`,
    options: {
      onSuccess: (created) => {
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

  // Wrapper that formats payload for the API — schema reducido propio
  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (payload: NuevaRevisionEdificacionesFormData) => {
        const { tarifas_ids, liquidacion_previa_id, ...rest } = payload;
        mutation.mutate({
          liquidacion_previa_id,
          liquidacion_general: {
            expediente: rest.expediente,
            observacion: rest.observacion,
            retencion: rest.retencion ?? false,
            ...(rest.contacto ? { contacto: rest.contacto } : {}),
          },
          liquidacion_especifica: {
            tarifas: (tarifas_ids || []).map((id) => ({
              tarifa_porcentaje_obra_id: id,
            })),
          },
        });
      },
      mutateAsync: async (payload: NuevaRevisionEdificacionesFormData) => {
        const { tarifas_ids, liquidacion_previa_id, ...rest } = payload;
        return mutation.mutateAsync({
          liquidacion_previa_id,
          liquidacion_general: {
            expediente: rest.expediente,
            observacion: rest.observacion,
            retencion: rest.retencion ?? false,
            ...(rest.contacto ? { contacto: rest.contacto } : {}),
          },
          liquidacion_especifica: {
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
