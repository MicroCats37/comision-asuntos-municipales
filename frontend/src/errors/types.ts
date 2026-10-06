/**
 * Standardized error shape returned by the error handler.
 * Every parser must produce this format.
 */
export interface ApiError {
  message: string;
  fieldErrors?: Record<string, string>;
  status?: number;
  raw?: unknown;
}

/**
 * An error parser attempts to extract a structured ApiError from a response.
 * Returns null if it cannot handle this error format (passes to next parser).
 */
export type ErrorParser = (status: number, data: unknown) => ApiError | null;
