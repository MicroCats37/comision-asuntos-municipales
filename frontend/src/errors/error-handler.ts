import type { AxiosError } from "axios";

import { normalizeErrorPayload } from "./error-normalizer";
import type { ApiError, ErrorParser } from "./types";

// =====================================================================
// BUILT-IN PARSERS (core — extensible via addErrorParser)
// =====================================================================

/**
 * Generic REST fallback
 * Format: { message: "..." } or { detail: "..." } or { error: { message, details } }
 * Also handles nested details: { error: { code, message, details: { non_field_errors, ... } } }
 * and the Django Ninja default validation body:
 * { detail: [{ loc: ["body", "field"], msg: "...", type: "..." }] }
 *
 * The normalization rules live in `error-normalizer.ts` so they can be reused
 * (and tested) outside of the parser chain.
 */
const genericRestParser: ErrorParser = (status, data) => {
  const normalized = normalizeErrorPayload(data);
  if (!normalized.message) return null;

  return {
    message: normalized.message,
    ...(normalized.fieldErrors ? { fieldErrors: normalized.fieldErrors } : {}),
    status,
  };
};

// =====================================================================
// PARSER CHAIN
// =====================================================================

const parsers: ErrorParser[] = [genericRestParser];

/**
 * Add a custom error parser to the chain.
 * Custom parsers are added to the FRONT of the chain (highest priority).
 *
 * @example
 * // In your project-specific setup:
 * addErrorParser((status, data: any) => {
 *   if (data?.code === "STRIPE_ERROR") {
 *     return { message: data.decline_message, status };
 *   }
 *   return null;
 * });
 */
export function addErrorParser(parser: ErrorParser) {
  parsers.unshift(parser);
}

// =====================================================================
// MAIN HANDLER
// =====================================================================

const DEFAULT_MESSAGES = {
  network: "No se pudo conectar con el servidor. Verifique su conexión.",
  unknown: "Ocurrió un error inesperado.",
  fallback: "Ocurrió un error al procesar la solicitud.",
};

/**
 * Processes any error (typically Axios) into a standardized ApiError.
 * Runs through the parser chain — first match wins.
 */
export function handleApiError(error: unknown): ApiError {
  const axiosError = error as AxiosError<unknown>;

  // No response at all (network error)
  if (!axiosError.response) {
    if (axiosError.request) {
      return { message: DEFAULT_MESSAGES.network, raw: error };
    }
    return {
      message: (axiosError as any)?.message || DEFAULT_MESSAGES.unknown,
      raw: error,
    };
  }

  const { status, data } = axiosError.response;

  // Run parser chain
  for (const parser of parsers) {
    const result = parser(status, data);
    if (result) {
      return { ...result, raw: error };
    }
  }

  // Nothing matched
  return {
    message: DEFAULT_MESSAGES.fallback,
    status,
    raw: error,
  };
}

/**
 * Convenience: always returns a string message.
 */
export function getErrorMessage(error: unknown): string {
  return handleApiError(error).message;
}
