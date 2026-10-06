/**
 * Standard API error detail (matches backend ErrorDetail).
 */
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

/**
 * Standard API response wrapper (matches backend ApiResponse[T]).
 * Backend: { success: bool, data: T | None, error: ErrorDetail | None }
 */
export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error?: ApiError;
  message?: string | null;
}

// ── Shared Zod Schemas for Runtime Validation ──────────────────────────────────

import { z } from "zod";

/** Shared error detail schema — matches ApiError shape */
export const apiErrorSchema = z.object({
  code: z.string(),
  message: z.string(),
  details: z.record(z.string(), z.any()).optional(),
});

/**
 * Creates a full API response envelope schema wrapping any data payload schema.
 * Use this instead of duplicating { success, data, error } Zod objects per hook.
 *
 * @example
 * const schema = apiResponseSchema(z.object({ igv_valor: z.number() }));
 */
export function apiResponseSchema<T>(dataSchema: z.ZodType<T>) {
  return z.object({
    success: z.boolean(),
    data: dataSchema.nullable(),
    error: apiErrorSchema.nullable().optional(),
    message: z.string().nullish().optional(),
  });
}

/**
 * Standard paginated response.
 * Matches Django Ninja/DRF pagination output by default.
 */
export interface PaginatedResponse<T> {
  data: T[];
  count: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

/**
 * Generic list params for paginated endpoints.
 */
export interface ListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  ordering?: string;
  [key: string]: unknown;
}
