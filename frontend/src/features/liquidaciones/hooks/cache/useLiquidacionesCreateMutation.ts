/**
 * useLiquidacionesCreateMutation
 *
 * Mutation hook especializado para liquidaciones que respeta el patrón de wrappers:
 * { liquidacion_general: { id, ... }, liquidacion_especifica, liquidacion_tipo }
 *
 * El id canónico se extrae como item.liquidacion_general.id.
 *
 * Comportamiento en onSuccess:
 * 1. Inserta el item en la lista tipo-específica (página 1, sin filtros)
 * 2. Inserta el item en la lista general "todas" (página 1)
 * 3. Hace seed del detalle tipo-específico: ["liquidaciones", tipoKey, id]
 * 4. Hace seed del detalle general: ["liquidaciones", "generales", id]
 *
 * No hace invalidateQueries — toda la actualización es manual.
 */

import {
  type MutationFunction,
  type UseMutationOptions,
  useMutation,
  useQueryClient,
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
 * Para nueva-revision/relacionada con lógica de ultimas-revisiones, usar
 * el refPattern:
 *
 *   const previousIdRef = useRef<string>();
 *   const mutation = useLiquidacionesCreateMutation({ tipoQueryKey, url });
 *   const cacheUtils = useLiquidacionesCacheUtils();
 *
 *   const crearMutation = useMemo(() => ({
 *     ...mutation,
 *     mutate: (data, previousId) => {
 *       previousIdRef.current = previousId;
 *       mutation.mutate(data);
 *     },
 *     mutateAsync: async (data, previousId) => {
 *       previousIdRef.current = previousId;
 *       return mutation.mutateAsync(data);
 *     },
 *   }), [mutation]);
 *
 *   // En options.onSuccess del mutation:
 *   // afterSuccess: (wrapper) => {
 *   //   if (previousIdRef.current) {
 *   //     cacheUtils.replaceLatestRevision(wrapper, { tipoKey, previousId: previousIdRef.current });
 *   //   }
 *   // }
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
  const queryClient = useQueryClient();
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

      const wrapperId = cacheUtils.getWrapperId(newItem);

      // ── 1) Lista tipo-específica paginada ──────────────────────────────────
      // El cache de useApiQuery guarda el envelope ApiResponse: { success, data: { items, total, page, ... } }.
      // Los updaters deben leer/escribir a través de `old.data.items` para que la preprenda
      // se refleje en la lista. El display layer (useLiquidacionList) ya desenvuelve `apiData.data`,
      // así que solo cambia la forma de lo escrito en cache.
      queryClient.setQueriesData<{
        success?: boolean;
        data: {
          items: LiquidacionWrapper[];
          total: number;
          total_pages?: number;
          page_size?: number;
          page?: number;
        } | null;
      }>({ queryKey: tipoQueryKey }, (old) => {
        if (!old?.data || !Array.isArray(old.data.items)) return old;
        const page = old.data.page ?? 1;
        if (page !== 1) return old;
        const pageSize = old.data.page_size;
        const items =
          insertPosition === "start"
            ? [newItem, ...old.data.items]
            : [...old.data.items, newItem];
        const trimmedItems = pageSize ? items.slice(0, pageSize) : items;
        return {
          ...old,
          data: {
            ...old.data,
            items: trimmedItems as LiquidacionWrapper[],
            total: (old.data.total ?? 0) + 1,
          },
        };
      });

      // ── 2) Lista general "todas" ───────────────────────────────────────────
      const generalesPrefijo = ["liquidaciones", "generales", "todas"] as const;
      queryClient.setQueriesData<{
        success?: boolean;
        data: {
          items: LiquidacionWrapper[];
          total: number;
          total_pages?: number;
          page_size?: number;
          page?: number;
        } | null;
      }>({ queryKey: generalesPrefijo }, (old) => {
        if (!old?.data || !Array.isArray(old.data.items)) return old;
        const page = old.data.page ?? 1;
        if (page !== 1) return old;
        const pageSize = old.data.page_size;
        const items =
          insertPosition === "start"
            ? [newItem, ...old.data.items]
            : [...old.data.items, newItem];
        const trimmedItems = pageSize ? items.slice(0, pageSize) : items;
        return {
          ...old,
          data: {
            ...old.data,
            items: trimmedItems as LiquidacionWrapper[],
            total: (old.data.total ?? 0) + 1,
          },
        };
      });

      // ── 3) Seed detail tipo-específico ────────────────────────────────────
      queryClient.setQueryData([...tipoQueryKey, wrapperId], newItem);

      // ── 4) Seed detail general ─────────────────────────────────────────────
      queryClient.setQueryData(
        ["liquidaciones", "generales", wrapperId],
        newItem,
      );
    },
    ...options,
  });
}
