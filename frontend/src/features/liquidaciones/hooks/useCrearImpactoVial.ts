/**
 * Hook para crear liquidaciones de Impacto Vial (primera revisión).
 * Usa useApiCreate genérico del proyecto.
 *
 * Endpoint: POST /liquidaciones/impacto-vial/primera-revision
 */
import { useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { useApiCreate } from "@/hooks";
import type { PorcentajeObraFormData } from "../schemas/liquidacion-porcentaje-form.schema";

const BASE_URL = "/liquidaciones/impacto-vial";

export function useCrearImpactoVial() {
  const queryClient = useQueryClient();

  const mutation = useApiCreate<unknown, { liquidacion_general: unknown; liquidacion_especifica: unknown }>({
    url: `${BASE_URL}/primera-revision`,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["liquidaciones", "impacto-vial"] });
      },
    },
  });

  // Wrapper that formats payload as { liquidacion_general, liquidacion_especifica } for the API
  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (payload: PorcentajeObraFormData) => {
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
      mutateAsync: async (payload: PorcentajeObraFormData) => {
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
