/**
 * Hook para crear una liquidación RELACIONADA de Edificaciones.
 *
 * POST /liquidaciones/edificaciones/relacionada
 * Payload: mismo shape que nueva-revision (liquidacion_previa_id singular).
 *
 * Usa useLiquidacionesCreateMutation (cache manual reactivo). La liquidación devuelta se inserta/actualiza en las listas visibles; la revisión previa permanece en la lista (ya no hay revisión canónica).
 */
import { useMemo } from "react";
import type { EdificacionesFormData } from "../schemas/liquidacion-edificaciones-form.schema";
import {
  construirEstrategiaPayload,
  ESTRATEGIA_NORMAL,
  leerEstrategiaFormData,
} from "../schemas/liquidacion-po-estrategia.schema";
import { useLiquidacionesCreateMutation } from "./cache";

const BASE_URL = "/liquidaciones/edificaciones";
const LIST_KEY = ["liquidaciones", "edificaciones"] as const;

/**
 * Payload de liquidación relacionada de Edificaciones.
 *
 * `numero_revision` viaja en el TOP LEVEL del body (contrato backend
 * `LiquidacionEdificacionesRelacionadaInput` = `NumeroRevisionRequeridoMixin`
 * + wrappers): es obligatorio y lo elige el usuario (etiqueta editable).
 */
export function buildCrearRelacionadaEdificacionesPayload(
  data: EdificacionesFormData,
  liquidacionPreviaId: string,
) {
  const {
    tarifa_unica_id,
    especialidades_seleccionadas,
    tipo_tramite,
    numero_revision,
    ...rest
  } = data;
  const {
    estrategia_cotizacion,
    valor_declarado,
    total_explicito,
  } = leerEstrategiaFormData(data);
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
    liquidacion_especifica: construirEstrategiaPayload({
      estrategia: estrategia_cotizacion ?? ESTRATEGIA_NORMAL,
      valor_declarado,
      total_explicito,
      tipo_tramite,
      tarifas: espIds.map((espId) => ({
        tarifa_porcentaje_obra_id: tarifa_unica_id as string,
        especialidad_id: espId,
      })),
    }),
  };
}

export function useCrearRelacionadaEdificaciones() {
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
      mutate: (data: EdificacionesFormData, liquidacionPreviaId: string) => {
        mutation.mutate(
          buildCrearRelacionadaEdificacionesPayload(data, liquidacionPreviaId),
        );
      },
      mutateAsync: async (
        data: EdificacionesFormData,
        liquidacionPreviaId: string,
      ) => {
        return mutation.mutateAsync(
          buildCrearRelacionadaEdificacionesPayload(data, liquidacionPreviaId),
        );
      },
    }),
    [mutation],
  );

  return crearMutation;
}
