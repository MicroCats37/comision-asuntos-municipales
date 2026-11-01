import { type UseMutationOptions, useMutation } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import type { ZodType } from "zod";
import {
  extractSuccessMessage,
  handleApiError,
  notify,
  recordSuccessMessage,
} from "@/errors";
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
        const response = await api.post(url, payload);
        // Surface the backend success message as toast when present.
        // The envelope message is authoritative; some endpoints nest it in `data`.
        const message = extractSuccessMessage(response.data);
        recordSuccessMessage(message);
        if (showToast && message) {
          notify.success(message);
        }
        return schema ? schema.parse(response.data) : (response.data as TData);
      } catch (error) {
        const apiError = handleApiError(error);
        if (showToast) notify.error(apiError.message);
        throw error;
      }
    },
    ...options,
  });
}
