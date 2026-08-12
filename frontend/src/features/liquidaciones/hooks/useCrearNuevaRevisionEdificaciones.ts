/**
 * Hook para crear NUEVA REVISIÓN de Edificaciones.
 * Usa useApiCreate genérico del proyecto.
 *
 * Endpoint: POST /liquidaciones/edificaciones/nueva-revision
 * Payload: { liquidacion_general, liquidacion_especifica, liquidacion_previa_id }
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

  // Wrapper that formats payload for the API
  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (payload: NuevaRevisionEdificacionesFormData) => {
        const { tarifas_ids, liquidacion_previa_id, ...rest } = payload;
        mutation.mutate({
          liquidacion_general: {
            municipalidad_id: rest.municipalidad_id,
            expediente: rest.expediente,
            observacion: rest.observacion,
            retencion: rest.retencion ?? false,
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
            ...(rest.contacto ? { contacto: rest.contacto } : {}),
          },
          liquidacion_especifica: {
            datos: {
              valor_declarado: rest.valor_declarado,
            },
            tarifas: (tarifas_ids || []).map((id) => ({
              tarifa_porcentaje_obra_id: id,
            })),
          },
          liquidacion_previa_id,
        });
      },
      mutateAsync: async (payload: NuevaRevisionEdificacionesFormData) => {
        const { tarifas_ids, liquidacion_previa_id, ...rest } = payload;
        return mutation.mutateAsync({
          liquidacion_general: {
            municipalidad_id: rest.municipalidad_id,
            expediente: rest.expediente,
            observacion: rest.observacion,
            retencion: rest.retencion ?? false,
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
            ...(rest.contacto ? { contacto: rest.contacto } : {}),
          },
          liquidacion_especifica: {
            datos: {
              valor_declarado: rest.valor_declarado,
            },
            tarifas: (tarifas_ids || []).map((id) => ({
              tarifa_porcentaje_obra_id: id,
            })),
          },
          liquidacion_previa_id,
        });
      },
    }),
    [mutation],
  );

  return crearMutation;
}
