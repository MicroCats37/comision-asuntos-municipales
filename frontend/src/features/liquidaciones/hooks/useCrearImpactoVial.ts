/**
 * Hook para crear liquidaciones de Impacto Vial (primera revisión).
 * Usa useApiCreate genérico del proyecto.
 *
 * Endpoint: POST /liquidaciones/impacto-vial/primera-revision
 */
import { useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { useApiCreate } from "@/hooks";
import type { ImpactoVialFormData } from "../schemas/liquidacion-impacto-vial-form.schema";

const BASE_URL = "/liquidaciones/impacto-vial";

export function useCrearImpactoVial() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<unknown, { liquidacion_general: unknown; liquidacion_especifica: unknown }>({
    url: `${BASE_URL}/primera-revision`,
    options: {
      onSuccess: (created) => {
        const newItem = (created as { data?: unknown })?.data ?? created;
        queryClient.setQueriesData<{ items: unknown[]; total: number }>(
          { queryKey: ["liquidaciones", "impacto-vial"] },
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
      mutate: (payload: ImpactoVialFormData) => {
        const { tarifa_unica_id, especialidades_seleccionadas, ...rest } = payload;
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
            tarifas: (especialidades_seleccionadas || []).map((espId) => ({
              tarifa_porcentaje_obra_id: tarifa_unica_id,
              especialidad_id: espId,
            })),
          },
        });
      },
      mutateAsync: async (payload: ImpactoVialFormData) => {
        const { tarifa_unica_id, especialidades_seleccionadas, ...rest } = payload;
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
            tarifas: (especialidades_seleccionadas || []).map((espId) => ({
              tarifa_porcentaje_obra_id: tarifa_unica_id,
              especialidad_id: espId,
            })),
          },
        });
      },
    }),
    [mutation],
  );

  return crearMutation;
}
