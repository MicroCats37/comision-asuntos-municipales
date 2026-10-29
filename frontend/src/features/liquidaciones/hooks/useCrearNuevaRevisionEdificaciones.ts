/**
 * Hook para crear NUEVA REVISIÓN de Edificaciones.
 *
 * POST /liquidaciones/edificaciones/nueva-revision
 * Payload:
 * {
 *   liquidacion_previa_id: uuid,
 *   liquidacion_general: { municipalidad, expediente, denominacion_de_proyecto, ...proyecto, contacto? },
 *   liquidacion_especifica: { tipo_tramite, datos: { valor_declarado }, tarifas: [...] }
 * }
 *
 * El form data tiene la misma forma que el form de crear (EdificacionesFormData);
 * el `liquidacion_previa_id` se pasa como argumento separado porque NO es un campo
 * del usuario — viene de la previa seleccionada.
 *
 * Usa useLiquidacionesCreateMutation (cache manual reactivo). La liquidación
 * devuelta se inserta/actualiza en las listas visibles; la revisión previa
 * permanece en la lista (ya no existe una "última revisión" canónica).
 */
import { useMemo } from "react";
import type { EdificacionesFormData } from "../schemas/liquidacion-edificaciones-form.schema";
import {
  ESTRATEGIA_NORMAL,
  ESTRATEGIA_TOTAL,
  leerEstrategiaFormData,
} from "../schemas/liquidacion-po-estrategia.schema";
import { useLiquidacionesCreateMutation } from "./cache";

const BASE_URL = "/liquidaciones/edificaciones";
const LIST_KEY = ["liquidaciones", "edificaciones"] as const;

/**
 * Payload de nueva revisión de Edificaciones.
 *
 * `numero_revision` viaja en el TOP LEVEL del body (contrato backend
 * `LiquidacionEdificacionesNuevaRevisionInput` = `NumeroRevisionRequeridoMixin`
 * + wrappers): es obligatorio y lo elige el usuario (etiqueta editable).
 *
 * `estrategia_cotizacion` viaja siempre: si se omite, el backend hereda la de
 * la previa, pero el formulario siempre la conoce (se rehidrata de la previa).
 * `datos` siempre conserva el valor declarado y TOTAL_EXPLICITO añade su total.
 */
export function buildCrearNuevaRevisionEdificacionesPayload(
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
  const estrategia = estrategia_cotizacion ?? ESTRATEGIA_NORMAL;
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
      tipo_tramite,
      estrategia_cotizacion: estrategia,
      // Los valores ausentes se omiten para que el backend los herede de la
      // revisión previa.
      datos:
        estrategia === ESTRATEGIA_TOTAL
          ? {
              ...(valor_declarado !== undefined ? { valor_declarado } : {}),
              ...(total_explicito !== undefined ? { total_explicito } : {}),
            }
          : valor_declarado !== undefined
            ? { valor_declarado }
            : {},
      tarifas: espIds.map((espId) => ({
        tarifa_porcentaje_obra_id: tarifa_unica_id,
        especialidad_id: espId,
      })),
    },
  };
}

export function useCrearNuevaRevisionEdificaciones() {
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
      mutate: (data: EdificacionesFormData, liquidacionPreviaId: string) => {
        mutation.mutate(
          buildCrearNuevaRevisionEdificacionesPayload(data, liquidacionPreviaId),
        );
      },
      mutateAsync: async (
        data: EdificacionesFormData,
        liquidacionPreviaId: string,
      ) => {
        return mutation.mutateAsync(
          buildCrearNuevaRevisionEdificacionesPayload(data, liquidacionPreviaId),
        );
      },
    }),
    [mutation],
  );

  return crearMutation;
}
