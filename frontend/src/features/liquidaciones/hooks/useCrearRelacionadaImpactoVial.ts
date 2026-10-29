/**
 * Hook para crear RELACIONADA de Impacto Vial.
 *
 * POST /liquidaciones/impacto-vial/relacionada
 * Payload: mismo shape que nueva-revision (liquidacion_previa_id singular).
 *
 * Usa useLiquidacionesCreateMutation (cache manual reactivo). La liquidación devuelta se inserta/actualiza en las listas visibles; la revisión previa permanece en la lista (ya no hay revisión canónica).
 */
import { useMemo } from "react";
import type { ImpactoVialFormData } from "../schemas/liquidacion-impacto-vial-form.schema";
import { useLiquidacionesCreateMutation } from "./cache";

const BASE_URL = "/liquidaciones/impacto-vial";
const LIST_KEY = ["liquidaciones", "impacto-vial"] as const;

/**
 * Payload de liquidación relacionada de Impacto Vial.
 *
 * `numero_revision` viaja en el TOP LEVEL del body (contrato backend
 * `LiquidacionImpactoVialRelacionadaInput` = `NumeroRevisionRequeridoMixin` +
 * wrappers): es obligatorio y lo elige el usuario (etiqueta editable).
 */
export function buildCrearRelacionadaImpactoVialPayload(
  data: ImpactoVialFormData,
  liquidacionPreviaId: string,
) {
  const {
    tarifa_unica_id,
    especialidades_seleccionadas,
    numero_revision,
    ...rest
  } = data;
  const espIds = especialidades_seleccionadas ?? [];
  return {
    liquidacion_previa_id: liquidacionPreviaId,
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
      ...(rest.contacto ? { contacto: rest.contacto } : {}),
    },
    liquidacion_especifica: {
      datos: {
        valor_declarado: rest.valor_declarado,
      },
      tarifas: espIds.map((espId) => ({
        tarifa_porcentaje_obra_id: tarifa_unica_id as string,
        especialidad_id: espId,
      })),
    },
  };
}

export function useCrearRelacionadaImpactoVial() {
  const mutation = useLiquidacionesCreateMutation<{
    liquidacion_general: unknown;
    liquidacion_especifica: unknown;
    liquidacion_previa_id: string;
    numero_revision: number;
  }>({
    tipoQueryKey: LIST_KEY,
    url: `${BASE_URL}/relacionada`,
  });

  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (data: ImpactoVialFormData, liquidacionPreviaId: string) => {
        mutation.mutate(
          buildCrearRelacionadaImpactoVialPayload(data, liquidacionPreviaId),
        );
      },
      mutateAsync: async (
        data: ImpactoVialFormData,
        liquidacionPreviaId: string,
      ) => {
        return mutation.mutateAsync(
          buildCrearRelacionadaImpactoVialPayload(data, liquidacionPreviaId),
        );
      },
    }),
    [mutation],
  );

  return crearMutation;
}
