/**
 * Hook para crear liquidaciones de Taludes (primera revisión).
 * Usa useGenericCreateMutation (cache de lista + detalle) + useApiCreate interno.
 *
 * Endpoint: POST /liquidaciones/taludes/primera-revision
 */
import { useMemo } from "react";
import { useGenericCreateMutation } from "@/hooks/cache";
import type { TaludesFormData } from "../schemas/liquidacion-taludes-form.schema";

const BASE_URL = "/liquidaciones/taludes";
const LIST_KEY = ["liquidaciones", "taludes"] as const;

export function useCrearTaludes() {
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
      mutate: (payload: TaludesFormData) => {
        const { tarifa_unica_id, especialidades_seleccionadas, ...rest } =
          payload;
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
            // Contacto principal (singular, opcional)
            ...(rest.contacto ? { contacto: rest.contacto } : {}),
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
      mutateAsync: async (payload: TaludesFormData) => {
        const { tarifa_unica_id, especialidades_seleccionadas, ...rest } =
          payload;
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
            // Contacto principal (singular, opcional)
            ...(rest.contacto ? { contacto: rest.contacto } : {}),
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
