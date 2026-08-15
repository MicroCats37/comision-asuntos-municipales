/**
 * Hook para crear liquidaciones de Mecánica de Suelos (primera revisión).
 * Usa useGenericCreateMutation (cache de lista + detalle) + useApiCreate interno.
 *
 * Endpoint: POST /liquidaciones/mecanica-suelos/nueva-liquidacion/primera-revision
 * Payload M2: liquidacion_especifica { datos: { area_solicitada }, tarifa: { tarifa_m2_id } }
 */
import { useMemo } from "react";
import { useGenericCreateMutation } from "@/hooks/cache";
import type { MecanicaSuelosFormData } from "../schemas/liquidacion-mecanica-suelos-form.schema";

const BASE_URL = "/liquidaciones/mecanica-suelos";
const LIST_KEY = ["liquidaciones", "mecanica-suelos"] as const;

export function useCrearMecanicaSuelos() {
  const mutation = useGenericCreateMutation<
    { id: string | number },
    { liquidacion_general: unknown; liquidacion_especifica: unknown }
  >({
    url: `${BASE_URL}/nueva-liquidacion/primera-revision`,
    queryKey: LIST_KEY,
    listShape: "paginated",
  });

  // Wrapper that formats payload as { liquidacion_general, liquidacion_especifica } for the API
  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (payload: MecanicaSuelosFormData) => {
        const { tarifa_m2_id, area_solicitada, ...rest } = payload;
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
              area_solicitada,
            },
            tarifa: tarifa_m2_id ? { tarifa_m2_id } : { tarifa_m2_id: "" },
          },
        });
      },
      mutateAsync: async (payload: MecanicaSuelosFormData) => {
        const { tarifa_m2_id, area_solicitada, ...rest } = payload;
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
              area_solicitada,
            },
            tarifa: tarifa_m2_id ? { tarifa_m2_id } : { tarifa_m2_id: "" },
          },
        });
      },
    }),
    [mutation],
  );

  return crearMutation;
}
