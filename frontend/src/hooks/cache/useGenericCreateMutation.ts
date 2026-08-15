import {
  type MutationFunction,
  type QueryKey,
  type UseMutationOptions,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import type { AxiosError } from "axios";
import type { ZodType } from "zod";
import { handleApiError, notify } from "@/errors";
import api from "@/lib/api";
import { buildApiPayload } from "@/utils";

interface UseGenericCreateMutationOptions<TVars = unknown> {
  queryKey: QueryKey;
  /**
   * URL del POST — construye el mutationFn internamente (buildApiPayload + api.post
   * + manejo de errores + toast), como useApiCreate. Alternativa a `mutationFn`.
   */
  url?: string;
  /** mutationFn manual (modo original). Se usa si no se provee `url`. */
  mutationFn?: MutationFunction<unknown, TVars>;
  schema?: ZodType<unknown>;
  showToast?: boolean;
  /** Dónde insertar en la lista: 'start' prepends (más reciente primero), 'end' append (más antiguo primero). Default: 'start' */
  insertPosition?: "start" | "end";
  /**
   * Shape del cache de la lista en `queryKey`:
   * - "array" (default): plain array `TItem[]`.
   * - "paginated": `{ items: TItem[]; total: number }` — usa setQueriesData
   *   por prefijo para cubrir las listas paginadas (page/page_size/filtros).
   */
  listShape?: "array" | "paginated";
  options?: Omit<UseMutationOptions<unknown, AxiosError, TVars>, "mutationFn">;
}

/**
 * Mutation de creación con sincronización de cache de lista + seed de detalle.
 *
 * Dos modos de creación:
 * - `url`: POST con buildApiPayload + toast de error (como useApiCreate).
 * - `mutationFn`: transformación manual (compatibilidad con el modo original).
 *
 * La mutation devuelve el envelope crudo de la API (como useApiCreate); el
 * unwrap del item de lista se hace en onSuccess para el prepend/append y el
 * seed del detalle en `[...queryKey, newItem.id]`.
 */
export function useGenericCreateMutation<
  TItem extends { id: string | number },
  TVars = unknown,
>({
  queryKey,
  url,
  mutationFn,
  schema,
  showToast = true,
  insertPosition = "start",
  listShape = "array",
  options,
}: UseGenericCreateMutationOptions<TVars>) {
  const queryClient = useQueryClient();

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
    : ((mutationFn ??
        (async () => {
          throw new Error(
            "useGenericCreateMutation: se requiere url o mutationFn",
          );
        })) as MutationFunction<unknown, TVars>);

  return useMutation<unknown, AxiosError, TVars>({
    mutationFn: internalMutationFn,
    onSuccess: (rawResult) => {
      // Desenvuelve el envelope ApiResponse para obtener el item de la lista
      const newItem = ((rawResult as { data?: TItem })?.data ??
        rawResult) as TItem;

      if (listShape === "paginated") {
        // Lista paginada { items, total } — matcheo parcial por prefijo
        queryClient.setQueriesData<{ items: TItem[]; total: number }>(
          { queryKey },
          (old) => {
            if (!old || !Array.isArray(old.items)) return old;
            return {
              ...old,
              items:
                insertPosition === "start"
                  ? [newItem, ...old.items]
                  : [...old.items, newItem],
              total: (old.total ?? 0) + 1,
            };
          },
        );
      } else {
        queryClient.setQueryData<TItem[]>(queryKey, (old) => {
          const list = old ?? [];
          return insertPosition === "start"
            ? [newItem, ...list]
            : [...list, newItem];
        });
      }
      // Seed detail cache
      queryClient.setQueryData([...queryKey, newItem.id], newItem);
    },
    ...options,
  });
}
