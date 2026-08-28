import {
  type QueryKey,
  type UseQueryOptions,
  useQuery,
} from "@tanstack/react-query";
import type { AxiosError } from "axios";
import type { ZodType } from "zod";
import { getErrorMessage, notify } from "@/errors";
import api from "@/lib/api";

interface UseApiQueryProps<T, TData = T> {
  queryKey: QueryKey;
  url: string | null;
  schema: ZodType<T>;
  params?: Record<string, unknown>;
  showToast?: boolean;
  queryOptions?: Omit<
    UseQueryOptions<T, ApiQueryError, TData>,
    "queryKey" | "queryFn"
  >;
}

/**
 * Error class that preserves axios response status for status-aware error handling.
 * Thrown instead of plain Error so callers can distinguish 404 (not found) from
 * 503/timeout (service unavailable).
 */
export class ApiQueryError extends Error {
  constructor(
    message: string,
    public readonly status: number | undefined,
  ) {
    super(message);
    this.name = "ApiQueryError";
  }
}

export function useApiQuery<T, TData = T>({
  queryKey,
  url,
  schema,
  params,
  showToast = true,
  queryOptions,
}: UseApiQueryProps<T, TData>) {
  const isEnabled = !!url && queryOptions?.enabled !== false;

  const finalQueryKey = params
    ? [...(Array.isArray(queryKey) ? queryKey : [queryKey]), params]
    : queryKey;

  return useQuery<T, ApiQueryError, TData>({
    queryKey: finalQueryKey,
    queryFn: async () => {
      if (!url) throw new Error("URL is required");

      try {
        const { data } = await api.get(url, { params });
        return schema.parse(data);
      } catch (error) {
        const axiosError = error as AxiosError;
        const msg = getErrorMessage(error);
        if (showToast) notify.error(msg);
        // Preserve status code so callers can distinguish error types
        throw new ApiQueryError(msg, axiosError.response?.status);
      }
    },
    enabled: isEnabled,
    // Type assertion needed: queryOptions uses Error type for compatibility,
    // but runtime behavior is correct since ApiQueryError extends Error
    ...(queryOptions as Omit<
      UseQueryOptions<T, ApiQueryError, TData>,
      "queryKey" | "queryFn"
    >),
  });
}
