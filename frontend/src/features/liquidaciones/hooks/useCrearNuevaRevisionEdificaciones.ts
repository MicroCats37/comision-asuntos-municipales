/**
 * Hook para crear NUEVA REVISIÓN de Edificaciones.
 * Usa useGenericCreateMutation (cache de lista + detalle) + useApiCreate interno.
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
import { useMemo } from "react";
import { useGenericCreateMutation } from "@/hooks/cache";
import type { NuevaRevisionEdificacionesFormData } from "../schemas/liquidacion-nueva-revision-form.schema";

const BASE_URL = "/liquidaciones/edificaciones";
const LIST_KEY = ["liquidaciones", "edificaciones"] as const;

export function useCrearNuevaRevisionEdificaciones() {
  const mutation = useGenericCreateMutation<
    { id: string | number },
    {
      liquidacion_general: unknown;
      liquidacion_especifica: unknown;
      liquidacion_previa_id: string;
    }
  >({
    url: `${BASE_URL}/nueva-revision`,
    queryKey: LIST_KEY,
    listShape: "paginated",
  });

  // Wrapper that formats payload for the API — schema reducido propio
  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (payload: NuevaRevisionEdificacionesFormData) => {
        const { tarifa_unica_id, especialidades_seleccionadas, liquidacion_previa_id, tipo_tramite, ...rest } = payload;
        mutation.mutate({
          liquidacion_previa_id,
          liquidacion_general: {
            expediente: rest.expediente,
            observacion: rest.observacion,
            retencion: rest.retencion ?? false,
            ...(rest.contacto ? { contacto: rest.contacto } : {}),
          },
          liquidacion_especifica: {
            tipo_tramite,
            tarifas: (especialidades_seleccionadas || []).map((espId) => ({
              tarifa_porcentaje_obra_id: tarifa_unica_id,
              especialidad_id: espId,
            })),
          },
        });
      },
      mutateAsync: async (payload: NuevaRevisionEdificacionesFormData) => {
        const { tarifa_unica_id, especialidades_seleccionadas, liquidacion_previa_id, tipo_tramite, ...rest } = payload;
        return mutation.mutateAsync({
          liquidacion_previa_id,
          liquidacion_general: {
            expediente: rest.expediente,
            observacion: rest.observacion,
            retencion: rest.retencion ?? false,
            ...(rest.contacto ? { contacto: rest.contacto } : {}),
          },
          liquidacion_especifica: {
            tipo_tramite,
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
