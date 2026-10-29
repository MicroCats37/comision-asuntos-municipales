/**
 * useLiquidacionesCreateMutation
 *
 * Mutation hook especializado para liquidaciones que respeta el patrón de wrappers:
 * { liquidacion_general: { id, ... }, liquidacion_especifica, liquidacion_tipo }
 *
 * El id canónico se extrae como item.liquidacion_general.id.
 *
 * Comportamiento en onSuccess (delegado a `useLiquidacionesCacheUtils`):
 * 1. Inserta/actualiza el item en la lista tipo-específica (página 1)
 * 2. Inserta/actualiza el item en la lista general "todas" (página 1)
 * 3. Hace seed del detalle tipo-específico: ["liquidaciones", tipoKey, id]
 * 4. Hace seed del detalle general: ["liquidaciones", "generales", id]
 *
 * NUNCA elimina registros existentes: ni la previa seleccionada ni sus
 * hermanos. Si el id ya está en la lista, se actualiza en su lugar.
 *
 * No hace invalidateQueries — toda la actualización es manual.
 */

import {
  type MutationFunction,
  type UseMutationOptions,
  useMutation,
} from "@tanstack/react-query";
import type { AxiosError } from "axios";
import type { ZodType } from "zod";
import { handleApiError, notify } from "@/errors";
import api from "@/lib/api";
import { buildApiPayload } from "@/utils";
import type { LiquidacionWrapper } from "./useLiquidacionesCacheUtils";
import { useLiquidacionesCacheUtils } from "./useLiquidacionesCacheUtils";

interface UseLiquidacionesCreateMutationOptions<TVars = unknown> {
  /** Query key base para la lista tipo-específica. Ej: ["liquidaciones", "edificaciones"] */
  tipoQueryKey: readonly [string, string];
  /** URL del POST */
  url?: string;
  /** mutationFn manual (reemplaza url). Se usa si no se provee `url`. */
  mutationFn?: MutationFunction<unknown, TVars>;
  schema?: ZodType<unknown>;
  showToast?: boolean;
  /** Dónde insertar en la lista: 'start' prepends (más reciente primero). Default: 'start' */
  insertPosition?: "start" | "end";
  options?: Omit<UseMutationOptions<unknown, AxiosError, TVars>, "mutationFn">;
}

/**
 * Wrapper de respuesta API para creaciones de liquidaciones.
 * El backend retorna: { success: true, data: LiquidacionWrapper }
 */
interface LiquidacionCreateResponse {
  success?: boolean;
  data?: LiquidacionWrapper;
  [key: string]: unknown;
}

/**
 * Hook de creación para liquidaciones con cache manual reactivo.
 *
 * Para nueva-revisión / relacionada NO hace falta ningún `onSuccess` propio:
 * el `onSuccess` interno ya inserta o actualiza la liquidación devuelta en las
 * listas visibles y en los detalles, SIN eliminar la previa seleccionada ni sus
 * hermanos (el modelo ya no tiene "revisión canónica").
 *
 * @example
 * const mutation = useLiquidacionesCreateMutation({
 *   tipoQueryKey: ["liquidaciones", "edificaciones"],
 *   url: "/liquidaciones/edificaciones/nueva-liquidacion/primera-revision",
 * });
 * mutation.mutate(payload);
 */
export function useLiquidacionesCreateMutation<TVars = unknown>({
  tipoQueryKey,
  url,
  mutationFn,
  schema,
  showToast = true,
  insertPosition = "start",
  options,
}: UseLiquidacionesCreateMutationOptions<TVars>) {
  const cacheUtils = useLiquidacionesCacheUtils();
  const internalMutationFn: MutationFunction<unknown, TVars> = url
    ? async (variables) => {
        try {
          const payload = buildApiPayload(variables);
          const { data } = await api.post(url, payload);
          return schema ? schema.parse(data) : data;
        } catch (error) {
          const apiError = handleApiError(error);
          if (showToast) notify.error(apiError.message);
          throw error;
        }
      }
    : (mutationFn ??
      ((async () => {
        throw new Error(
          "useLiquidacionesCreateMutation: se requiere url o mutationFn",
        );
      }) as MutationFunction<unknown, TVars>));

  return useMutation<unknown, AxiosError, TVars>({
    mutationFn: internalMutationFn,
    onSuccess: (rawResult) => {
      // Desenvuelve el wrapper de la respuesta API
      const response = rawResult as LiquidacionCreateResponse;
      const newItem: LiquidacionWrapper =
        response?.data ?? (rawResult as LiquidacionWrapper);

      // Validar que tenemos un wrapper válido
      if (
        !newItem ||
        typeof newItem !== "object" ||
        !newItem.liquidacion_general
      ) {
        // Wrapper inesperado — fallback: no hacer nada en cache
        return;
      }

      // ── Listas + detalles ─────────────────────────────────────────────────
      // Inserción/actualización sin eliminar NUNCA la previa seleccionada ni sus
      // hermanos: la revisión nueva_convive con la revisión de la que nació.
      cacheUtils.upsertCreatedItem(newItem, {
        tipoKey: tipoQueryKey[1],
        position: insertPosition,
      });
    },
    ...options,
  });
}
