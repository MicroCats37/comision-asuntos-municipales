/**
 * Hook para crear liquidaciones de Edificaciones (primera revisión).
 * Usa useLiquidacionesCreateMutation (cache manual reactivo) + useApiCreate interno.
 *
 * Endpoint: POST /liquidaciones/edificaciones/nueva-liquidacion/primera-revision
 */
import { useMemo } from "react";
import type { EdificacionesFormData } from "../schemas/liquidacion-edificaciones-form.schema";
import { useLiquidacionesCreateMutation } from "./cache";

const BASE_URL = "/liquidaciones/edificaciones/nueva-liquidacion";
const LIST_KEY = ["liquidaciones", "edificaciones"] as const;

export function useCrearEdificaciones() {
  const mutation = useLiquidacionesCreateMutation<{
    liquidacion_general: unknown;
    liquidacion_especifica: unknown;
  }>({
    tipoQueryKey: LIST_KEY,
    url: `${BASE_URL}/primera-revision`,
  });

  // Wrapper that formats payload as { liquidacion_general, liquidacion_especifica } for the API
  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (payload: EdificacionesFormData) => {
        const {
          tarifa_unica_id,
          especialidades_seleccionadas,
          tipo_tramite,
          ...rest
        } = payload;
        mutation.mutate({
          liquidacion_general: {
            municipalidad_id: rest.municipalidad_id,
            expediente: rest.expediente,
            observacion: rest.observacion,
            retencion: rest.retencion ?? false,
            denominacion_de_proyecto: rest.denominacion || undefined,
            proyecto: {
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
            tipo_tramite,
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
      mutateAsync: async (payload: EdificacionesFormData) => {
        const {
          tarifa_unica_id,
          especialidades_seleccionadas,
          tipo_tramite,
          ...rest
        } = payload;
        return mutation.mutateAsync({
          liquidacion_general: {
            municipalidad_id: rest.municipalidad_id,
            expediente: rest.expediente,
            observacion: rest.observacion,
            retencion: rest.retencion ?? false,
            denominacion_de_proyecto: rest.denominacion || undefined,
            proyecto: {
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
            tipo_tramite,
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
