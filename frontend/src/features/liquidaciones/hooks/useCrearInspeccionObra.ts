/**
 * Hook para crear liquidaciones de Inspección de Obra (primera revisión).
 * Usa useGenericCreateMutation (cache de lista + detalle) + useApiCreate interno.
 *
 * Endpoint: POST /liquidaciones/inspeccion-obra/primera-revision
 */
import { useMemo } from "react";
import { useGenericCreateMutation } from "@/hooks/cache";
import type { VisitasFormData } from "../schemas/liquidacion-visitas-form.schema";

const BASE_URL = "/liquidaciones/inspeccion-obra";
const LIST_KEY = ["liquidaciones", "inspeccion-obra"] as const;

export function useCrearInspeccionObra() {
  const mutation = useGenericCreateMutation<
    { id: string | number },
    { liquidacion_general: unknown; liquidacion_especifica: unknown }
  >({
    url: `${BASE_URL}/primera-revision`,
    queryKey: LIST_KEY,
    listShape: "paginated",
  });

  // Wrapper that formats payload as { liquidacion_general, liquidacion_especifica } for the API
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
        const { tarifa_visitas_id, cantidad_visitas, categoria, ...rest } =
          payload;
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
