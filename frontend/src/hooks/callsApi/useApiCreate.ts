import { type UseMutationOptions, useMutation } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import type { ZodType } from "zod";
import { getErrorMessage, handleApiError, notify } from "@/errors";
import api from "@/lib/api";
import { buildApiPayload } from "@/utils";

interface UseApiCreateProps<TData, TVariables> {
  url: string;
  schema?: ZodType<TData>;
  showToast?: boolean;
  options?: Omit<
    UseMutationOptions<TData, AxiosError, TVariables>,
    "mutationFn"
  >;
}

export function useApiCreate<TData = unknown, TVariables = unknown>({
  url,
  schema,
  showToast = true,
  options,
}: UseApiCreateProps<TData, TVariables>) {
  return useMutation<TData, AxiosError, TVariables>({
    mutationFn: async (variables) => {
      try {
        const payload = buildApiPayload(variables);
        const { data } = await api.post(url, payload);
        return schema ? schema.parse(data) : (data as TData);
      } catch (error) {
        const apiError = handleApiError(error);
        if (showToast) notify.error(apiError.message);
        throw error;
      }
    },
    ...options,
  });
}
