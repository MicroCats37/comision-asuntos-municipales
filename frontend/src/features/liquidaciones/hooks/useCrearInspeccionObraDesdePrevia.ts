/**
 * Hook para crear una Inspección de Obra PRIMERA-REVISIÓN desde una liquidación previa.
 * Usa useGenericCreateMutation (cache de lista + detalle) + useApiCreate interno.
 *
 * Endpoint: POST /liquidaciones/inspeccion-obra/nueva-liquidacion
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
import { useMemo } from "react";
import { useGenericCreateMutation } from "@/hooks/cache";
import type { NuevaRevisionInspeccionObraFormData } from "../schemas/liquidacion-nueva-revision-io.schema";

const BASE_URL = "/liquidaciones/inspeccion-obra";
const LIST_KEY = ["liquidaciones", "inspeccion-obra"] as const;

export function useCrearInspeccionObraDesdePrevia() {
  const mutation = useGenericCreateMutation<
    { id: string | number },
    {
      liquidacion_previa_id: string;
      liquidacion_especifica: {
        datos: { cantidad_visitas: number; categoria: string };
        tarifa: { tarifa_visitas_id: string };
        inspector_id: string;
      };
    }
  >({
    url: `${BASE_URL}/nueva-liquidacion`,
    queryKey: LIST_KEY,
    listShape: "paginated",
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
