/**
 * Hook para crear liquidaciones de Taludes (primera revisión).
 * Usa useLiquidacionesCreateMutation (cache manual reactivo) + useApiCreate interno.
 *
 * Endpoint: POST /liquidaciones/taludes/primera-revision
 */
import { useMemo } from "react";
import type { TaludesFormData } from "../schemas/liquidacion-taludes-form.schema";
import { useLiquidacionesCreateMutation } from "./cache";

const BASE_URL = "/liquidaciones/taludes";
const LIST_KEY = ["liquidaciones", "taludes"] as const;

/**
 * Payload de creación (primera-revisión) de Taludes.
 *
 * `numero_revision` viaja en el TOP LEVEL del body (contrato backend
 * `LiquidacionTaludesInput` = `NumeroRevisionRequeridoMixin` + wrappers):
 * es obligatorio y lo elige el usuario.
 */
export function buildCrearTaludesPayload(payload: TaludesFormData) {
  const {
    tarifa_unica_id,
    especialidades_seleccionadas,
    numero_revision,
    ...rest
  } = payload;
  return {
    numero_revision,
    liquidacion_general: {
      municipalidad_id: rest.municipalidad_id,
      expediente: rest.expediente,
      observacion: rest.observacion,
      denominacion_de_proyecto: rest.denominacion || undefined,
      proyecto: {
        nombre_propietario: rest.nombre_propietario,
        direccion: rest.direccion,
        distrito_id: rest.distrito_id || undefined,
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
  };
}

export function useCrearTaludes() {
  const mutation = useLiquidacionesCreateMutation<{
    liquidacion_general: unknown;
    liquidacion_especifica: unknown;
    numero_revision: number;
  }>({
    tipoQueryKey: LIST_KEY,
    url: `${BASE_URL}/nueva-liquidacion/primera-revision`,
  });

  // Wrapper that formats payload as { liquidacion_general, liquidacion_especifica } for the API
  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (payload: TaludesFormData) => {
        mutation.mutate(buildCrearTaludesPayload(payload));
      },
      mutateAsync: async (payload: TaludesFormData) => {
        return mutation.mutateAsync(buildCrearTaludesPayload(payload));
      },
    }),
    [mutation],
  );

  return crearMutation;
}
