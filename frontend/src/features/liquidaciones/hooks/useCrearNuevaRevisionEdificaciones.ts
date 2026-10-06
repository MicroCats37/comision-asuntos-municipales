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
 * Usa useLiquidacionesCreateMutation (cache manual reactivo) con lógica de ultimas-revisiones.
 * La revisión previa se remueve de ultimas-revisiones y la nueva se inserta.
 */
import { useMemo, useRef } from "react";
import type { EdificacionesFormData } from "../schemas/liquidacion-edificaciones-form.schema";
import type { LiquidacionWrapper } from "./cache";
import {
  useLiquidacionesCacheUtils,
  useLiquidacionesCreateMutation,
} from "./cache";

const BASE_URL = "/liquidaciones/edificaciones";
const LIST_KEY = ["liquidaciones", "edificaciones"] as const;
const TIPO_KEY = "edificaciones";

function buildPayload(
  data: EdificacionesFormData,
  liquidacionPreviaId: string,
) {
  const {
    tarifa_unica_id,
    especialidades_seleccionadas,
    tipo_tramite,
    ...rest
  } = data;
  const espIds = especialidades_seleccionadas ?? [];
  return {
    liquidacion_previa_id: liquidacionPreviaId,
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
      ...(rest.contacto ? { contacto: rest.contacto } : {}),
    },
    liquidacion_especifica: {
      tipo_tramite,
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

export function useCrearNuevaRevisionEdificaciones() {
  const previousIdRef = useRef<string | null>(null);
  const cacheUtils = useLiquidacionesCacheUtils();

  const mutation = useLiquidacionesCreateMutation<{
    liquidacion_general: unknown;
    liquidacion_especifica: unknown;
    liquidacion_previa_id: string;
  }>({
    tipoQueryKey: LIST_KEY,
    url: `${BASE_URL}/nueva-revision`,
    options: {
      onSuccess: (rawResult) => {
        // Replicate basic cache updates (same as internal onSuccess of useLiquidacionesCreateMutation)
        const response = rawResult as { data?: LiquidacionWrapper };
        const newItem: LiquidacionWrapper =
          response?.data ?? (rawResult as LiquidacionWrapper);
        if (!newItem?.liquidacion_general?.id) return;

        const wrapperId = String(newItem.liquidacion_general.id);

        // Basic cache updates (from useLiquidacionesCreateMutation's internal onSuccess)
        // These mirror the internal logic since we override onSuccess:
        cacheUtils.removeVisibleItem(wrapperId); // remove from type-specific + general lists (item not yet there, no-op)
        // Actually: since this is a NEW item, we need to INSERT it (useLiquidacionesCreateMutation inserts)
        // But since we override onSuccess, we do ALL cache updates here:

        // Insert into type-specific list (page 1) — handled by replaceLatestRevision too if page 1
        cacheUtils.insertCreatedItem(newItem, { tipoKey: TIPO_KEY });

        // Seed detail caches
        cacheUtils.markDetailDeleted(wrapperId); // no-op since it's new

        // ultimas-revisiones: replace previous with new
        const prevId = previousIdRef.current;
        if (prevId) {
          cacheUtils.replaceLatestRevision(newItem, {
            tipoKey: TIPO_KEY,
            previousId: prevId,
          });
        }
      },
    },
  });

  const crearMutation = useMemo(
    () => ({
      ...mutation,
      mutate: (data: EdificacionesFormData, liquidacionPreviaId: string) => {
        previousIdRef.current = liquidacionPreviaId;
        mutation.mutate(buildPayload(data, liquidacionPreviaId));
      },
      mutateAsync: async (
        data: EdificacionesFormData,
        liquidacionPreviaId: string,
      ) => {
        previousIdRef.current = liquidacionPreviaId;
        return mutation.mutateAsync(buildPayload(data, liquidacionPreviaId));
      },
    }),
    [mutation],
  );

  return crearMutation;
}
