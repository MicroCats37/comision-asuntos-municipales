/**
 * Central extraction of the human-readable success message carried by the API
 * envelope (contract/next-app-architecture-contract.md §11).
 *
 * The envelope shape is `{ success, data, error, message }`. Some endpoints
 * nest their message inside `data` (e.g. the delete endpoints of the
 * `finanzas` module), so both locations are supported: the top-level message
 * always wins.
 */

import { isPlainObject } from "./error-normalizer";

function toText(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

/**
 * Returns the success message of an API envelope, or `undefined` when the
 * endpoint does not provide one (silent read/preview endpoints, login, ...).
 */
export function extractSuccessMessage(envelope: unknown): string | undefined {
  if (!isPlainObject(envelope)) return undefined;

  const topLevel = toText(envelope.message);
  if (topLevel) return topLevel;

  const data = envelope.data;
  if (isPlainObject(data)) {
    const nested = toText(data.message);
    if (nested) return nested;
  }

  return undefined;
}

/**
 * Registry of the last success message published by the mutation layer.
 *
 * `GenericForm` renders its success banner from this registry because the
 * banner and the toast are produced by two different layers (the mutation
 * hook owns the toast, the form owns the inline banner).
 */
let lastSuccessMessage: string | undefined;

/** Publishes the success message of the last completed mutation. */
export function recordSuccessMessage(message: string | undefined): void {
  lastSuccessMessage = toText(message);
}

/** Reads the last published success message without clearing it. */
export function peekSuccessMessage(): string | undefined {
  return lastSuccessMessage;
}

/** Clears the registry (called right before a form submission starts). */
export function clearSuccessMessage(): void {
  lastSuccessMessage = undefined;
}
