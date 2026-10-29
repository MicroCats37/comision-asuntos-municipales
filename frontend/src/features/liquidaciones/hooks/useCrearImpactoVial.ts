/**
 * Hook para crear liquidaciones de Impacto Vial (primera revisión).
 * Usa useLiquidacionesCreateMutation (cache manual reactivo) + useApiCreate interno.
 *
 * Endpoint: POST /liquidaciones/impacto-vial/primera-revision
 */
import { useMemo } from "react";
import type { ImpactoVialFormData } from "../schemas/liquidacion-impacto-vial-form.schema";
import { useLiquidacionesCreateMutation } from "./cache";

const BASE_URL = "/liquidaciones/impacto-vial";
const LIST_KEY = ["liquidaciones", "impacto-vial"] as const;

/**
 * Payload de creación (primera-revisión) de Impacto Vial.
 *
 * `numero_revision` viaja en el TOP LEVEL del body (contrato backend
 * `LiquidacionImpactoVialInput` = `NumeroRevisionRequeridoMixin` + wrappers):
 * es obligatorio y lo elige el usuario.
 */
export function buildCrearImpactoVialPayload(payload: ImpactoVialFormData) {
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

export function useCrearImpactoVial() {
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
      mutate: (payload: ImpactoVialFormData) => {
        mutation.mutate(buildCrearImpactoVialPayload(payload));
      },
      mutateAsync: async (payload: ImpactoVialFormData) => {
        return mutation.mutateAsync(buildCrearImpactoVialPayload(payload));
      },
    }),
    [mutation],
  );

  return crearMutation;
}
