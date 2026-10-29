/**
 * Hook para crear NUEVA REVISIÓN de Impacto Vial.
 *
 * POST /liquidaciones/impacto-vial/nueva-revision
 * Payload: { liquidacion_previa_id, liquidacion_general, liquidacion_especifica }
 *
 * Usa useLiquidacionesCreateMutation (cache manual reactivo). La liquidación devuelta se inserta/actualiza en las listas visibles; la revisión previa permanece en la lista (ya no hay revisión canónica).
 */
import { useMemo } from "react";
import type { ImpactoVialFormData } from "../schemas/liquidacion-impacto-vial-form.schema";
import { useLiquidacionesCreateMutation } from "./cache";

const BASE_URL = "/liquidaciones/impacto-vial";
const LIST_KEY = ["liquidaciones", "impacto-vial"] as const;

/**
 * Payload de nueva revisión de Impacto Vial.
 *
 * `numero_revision` viaja en el TOP LEVEL del body (contrato backend
 * `LiquidacionImpactoVialNuevaRevisionInput` = `NumeroRevisionRequeridoMixin`
 * + wrappers): es obligatorio y lo elige el usuario (etiqueta editable).
 */
export function buildCrearNuevaRevisionImpactoVialPayload(
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

export function useCrearNuevaRevisionImpactoVial() {
  const mutation = useLiquidacionesCreateMutation<{
    liquidacion_general: unknown;
    liquidacion_especifica: unknown;
    liquidacion_previa_id: string;
    numero_revision: number;
  }>({
    tipoQueryKey: LIST_KEY,
    url: `${BASE_URL}/nueva-revision`,
  });

  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (data: ImpactoVialFormData, liquidacionPreviaId: string) => {
        mutation.mutate(
          buildCrearNuevaRevisionImpactoVialPayload(data, liquidacionPreviaId),
        );
      },
      mutateAsync: async (
        data: ImpactoVialFormData,
        liquidacionPreviaId: string,
      ) => {
        return mutation.mutateAsync(
          buildCrearNuevaRevisionImpactoVialPayload(data, liquidacionPreviaId),
        );
      },
    }),
    [mutation],
  );

  return crearMutation;
}
