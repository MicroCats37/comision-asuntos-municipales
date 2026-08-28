import {
  type UseMutateFunction,
  type UseMutationOptions,
  type UseMutationResult,
  useMutation,
} from "@tanstack/react-query";
import type { AxiosError } from "axios";
import type { ZodType } from "zod";
import { handleApiError, notify } from "@/errors";
import api from "@/lib/api";
import { buildApiPayload } from "@/utils";

// ---------------------------------------------------------------------------
// Variable types
// ---------------------------------------------------------------------------

/** Classic backward-compatible shape: caller provides id + data. */
type ClassicVariables<TPayload> = {
  id: number | string;
  data: TPayload;
};

/** Direct payload shape (like useApiCreate): variable IS the payload. */
type DirectVariables<TPayload> = TPayload;

// ---------------------------------------------------------------------------
// Props — two modes
// ---------------------------------------------------------------------------

/** Direct-mode props (url provided): behaves like useApiCreate. */
interface UseApiUpdateDirectProps<TData, TVariables> {
  /** Direct URL for the endpoint. Variables are sent as-is as payload. */
  url: string;
  schema?: ZodType<TData>;
  method?: "PUT" | "PATCH";
  showToast?: boolean;
  options?: Omit<
    UseMutationOptions<TData, AxiosError, DirectVariables<TVariables>>,
    "mutationFn"
  >;
}

/** Classic-mode props (baseUrl provided): expects { id, data } variables. */
interface UseApiUpdateClassicProps<TData, TPayload> {
  /** Base URL; id is appended automatically. */
  baseUrl: string;
  schema?: ZodType<TData>;
  method?: "PUT" | "PATCH";
  showToast?: boolean;
  options?: Omit<
    UseMutationOptions<TData, AxiosError, ClassicVariables<TPayload>>,
    "mutationFn"
  >;
}

// ---------------------------------------------------------------------------
// Hook with overloads for clean typing
// ---------------------------------------------------------------------------

/**
 * Unified update hook supporting two calling conventions:
 *
 * **Direct mode** (url prop — like useApiCreate):
 *   const m = useApiUpdate({ url: `/bungalows/${id}/imagenes` })
 *   m.mutate(payload)   // payload goes directly through buildApiPayload
 *
 * **Classic mode** (baseUrl prop — backward-compatible):
 *   const m = useApiUpdate({ baseUrl: "/users" })
 *   m.mutate({ id: 5, data: { name: "Ana" } })  // PATCH /users/5 with data
 */

// Overload 1: direct mode
export function useApiUpdate<TData, TVariables>(
  props: UseApiUpdateDirectProps<TData, TVariables>,
): UseMutationResult<TData, AxiosError, DirectVariables<TVariables>>;

// Overload 2: classic mode
export function useApiUpdate<TData, TPayload>(
  props: UseApiUpdateClassicProps<TData, TPayload>,
): UseMutationResult<TData, AxiosError, ClassicVariables<TPayload>>;

// Implementation
export function useApiUpdate<TData, TVariables>(
  props:
    | UseApiUpdateDirectProps<TData, TVariables>
    | UseApiUpdateClassicProps<TData, TVariables>,
): UseMutationResult<TData, AxiosError, TVariables> {
  // ------------------------------------------------------------------
  // Detect mode: 'url' key present means direct mode
  // ------------------------------------------------------------------
  const isDirectMode =
    "url" in props &&
    (props as UseApiUpdateDirectProps<TData, TVariables>).url !== undefined;

  if (isDirectMode) {
    const {
      url,
      schema,
      method = "PUT",
      showToast = true,
      options,
    } = props as UseApiUpdateDirectProps<TData, TVariables>;

    return useMutation<TData, AxiosError, DirectVariables<TVariables>>({
      mutationFn: async (variables) => {
        try {
          const payload = buildApiPayload(variables);
          const { data } = await api.request({ url, method, data: payload });
          return schema ? schema.parse(data) : (data as TData);
        } catch (error) {
          const apiError = handleApiError(error);
          if (showToast) notify.error(apiError.message);
          throw error;
        }
      },
      ...options,
    }) as unknown as UseMutationResult<TData, AxiosError, TVariables>;
  }

  // ------------------------------------------------------------------
  // Classic mode: baseUrl + { id, data }
  // ------------------------------------------------------------------
  const {
    baseUrl,
    schema,
    method = "PUT",
    showToast = true,
    options,
  } = props as UseApiUpdateClassicProps<TData, TVariables>;

  return useMutation<TData, AxiosError, ClassicVariables<TVariables>>({
    mutationFn: async ({ id, data }) => {
      try {
        const payload = buildApiPayload(data);
        const { data: responseData } = await api.request({
          url: `${baseUrl}/${id}`,
          method,
          data: payload,
        });
        return schema ? schema.parse(responseData) : (responseData as TData);
      } catch (error) {
        const apiError = handleApiError(error);
        if (showToast) notify.error(apiError.message);
        throw error;
      }
    },
    ...options,
  }) as unknown as UseMutationResult<TData, AxiosError, TVariables>;
}
