/**
 * Central, dependency-free normalization of API error payloads.
 *
 * Goals (contract/next-app-architecture-contract.md §11):
 * - Produce ONE human-readable message per failure.
 * - Never render the wire key `non_field_errors` (nor any label for it).
 * - Keep the labels of REAL fields so they can be attached to the inputs.
 *
 * The module is intentionally pure (no React, no side effects) so it can be
 * unit-tested in isolation and reused by every consumer.
 */

/** Backend wire key used for errors that do not belong to a specific field. */
export const GLOBAL_ERROR_KEY = "non_field_errors";

/** Separator used when several messages are merged into a single line. */
export const MESSAGE_SEPARATOR = "; ";

export interface NormalizedError {
  /** Human-readable message. Never contains the global error key. */
  message?: string;
  /** Per-field messages keyed by the real field path. Never contains the global key. */
  fieldErrors?: Record<string, string>;
}

export interface FlattenedDetails {
  /** Field messages already labeled, e.g. `email: Ingresa un correo válido.` */
  fieldMessages: string[];
  /** Global messages without any label. */
  globalMessages: string[];
  /** Field path -> message for REAL fields only. */
  fieldErrors: Record<string, string>;
}

export function isPlainObject(
  value: unknown,
): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Converts a scalar into a displayable text.
 * Numbers and booleans are accepted so a numeric `details` value never crashes.
 */
function toText(value: unknown): string | undefined {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : undefined;
  }
  if (typeof value === "number") {
    return Number.isFinite(value) ? String(value) : undefined;
  }
  if (typeof value === "boolean") {
    return String(value);
  }
  return undefined;
}

/**
 * Same as {@link toText} but also accepts a list of texts (e.g. an
 * `error.message` array) joining them with the standard separator.
 */
export function toTextOrJoined(value: unknown): string | undefined {
  if (Array.isArray(value)) {
    const parts = value
      .map((item) => toText(item))
      .filter((item): item is string => item !== undefined);
    return parts.length > 0 ? parts.join(MESSAGE_SEPARATOR) : undefined;
  }
  return toText(value);
}

/**
 * Walks a `details` payload and splits it into labeled field messages and
 * unlabeled global messages.
 *
 * The global key (`non_field_errors`) and the empty key are treated as global:
 * their content is kept, their key is never rendered.
 */
export function flattenValidationDetails(details: unknown): FlattenedDetails {
  const result: FlattenedDetails = {
    fieldMessages: [],
    globalMessages: [],
    fieldErrors: {},
  };

  const walk = (value: unknown, path: string[], isGlobal: boolean): void => {
    const text = toText(value);
    if (text !== undefined) {
      if (isGlobal || path.length === 0) {
        result.globalMessages.push(text);
        return;
      }
      const label = path.join(".");
      result.fieldMessages.push(`${label}: ${text}`);
      result.fieldErrors[label] = result.fieldErrors[label]
        ? `${result.fieldErrors[label]} ${text}`
        : text;
      return;
    }

    if (Array.isArray(value)) {
      for (const item of value) walk(item, path, isGlobal);
      return;
    }

    if (isPlainObject(value)) {
      for (const [key, item] of Object.entries(value)) {
        const itemIsGlobal = isGlobal || key === GLOBAL_ERROR_KEY || key === "";
        walk(item, itemIsGlobal ? [] : [...path, key], itemIsGlobal);
      }
    }
  };

  walk(details, [], false);
  return result;
}

/**
 * Django Ninja / Pydantic default 422 body:
 * `{ detail: [{ loc: ["body", "email"], msg: "...", type: "..." }] }`
 */
export function flattenNinjaDetail(detail: unknown[]): string[] {
  const messages: string[] = [];

  for (const entry of detail) {
    if (!isPlainObject(entry)) {
      const text = toText(entry);
      if (text) messages.push(text);
      continue;
    }

    const msg = toText(entry.msg);
    if (!msg) continue;

    const loc = entry.loc;
    const lastSegment = Array.isArray(loc)
      ? loc.filter(
          (part) => typeof part === "string" || typeof part === "number",
        )
      : [];
    const label =
      lastSegment.length > 0 ? String(lastSegment[lastSegment.length - 1]) : "";

    messages.push(label ? `${label}: ${msg}` : msg);
  }

  return messages;
}

/**
 * Normalizes any API error payload into a single message plus the per-field
 * errors of the REAL fields.
 *
 * Precedence:
 * 1. `error` object with `code === "VALIDATION_ERROR"` or real field keys →
 *    build the message from `details` (labels preserved, global key dropped).
 * 2. `error.message` (string or list) → used verbatim.
 * 3. `errors.message` / `message` / `detail` → used verbatim.
 * 4. `detail[]` (Ninja) → `campo: mensaje`.
 * 5. Plain string / number body → its text form.
 * 6. Otherwise → nothing (the caller applies its own fallback).
 */
export function normalizeErrorPayload(data: unknown): NormalizedError {
  const result: NormalizedError = {};

  // 5. Plain string / number body (non-JSON responses).
  if (typeof data === "string" || typeof data === "number") {
    const text = toText(data);
    if (text) result.message = text;
    return result;
  }

  if (!isPlainObject(data)) return result;

  const errorNode = data.error;

  // 1/2. CAM error envelope.
  if (isPlainObject(errorNode)) {
    const code =
      typeof errorNode.code === "string" ? errorNode.code : undefined;
    const details = flattenValidationDetails(errorNode.details);
    const hasFieldErrors = Object.keys(details.fieldErrors).length > 0;

    if (code === "VALIDATION_ERROR" || hasFieldErrors) {
      const message = [
        ...details.fieldMessages,
        ...details.globalMessages,
      ].join(MESSAGE_SEPARATOR);
      if (message) {
        result.message = message;
        if (hasFieldErrors) result.fieldErrors = details.fieldErrors;
        return result;
      }
    }

    const envelopeMessage = toTextOrJoined(errorNode.message);
    if (envelopeMessage) {
      result.message = envelopeMessage;
      if (hasFieldErrors) result.fieldErrors = details.fieldErrors;
      return result;
    }

    if (details.globalMessages.length > 0) {
      result.message = details.globalMessages.join(MESSAGE_SEPARATOR);
      return result;
    }
  } else if (typeof errorNode === "string") {
    const text = toText(errorNode);
    if (text) {
      result.message = text;
      return result;
    }
  }

  // 3. Alternative envelope shapes.
  const errorsNode = isPlainObject(data.errors) ? data.errors : undefined;
  const directMessage =
    toTextOrJoined(errorsNode?.message) ?? toTextOrJoined(data.message);
  if (directMessage) {
    result.message = directMessage;
    return result;
  }

  // 4. Ninja default validation body.
  if (Array.isArray(data.detail)) {
    const messages = flattenNinjaDetail(data.detail);
    if (messages.length > 0) {
      result.message = messages.join(MESSAGE_SEPARATOR);
      return result;
    }
  } else {
    const detailText = toTextOrJoined(data.detail);
    if (detailText) {
      result.message = detailText;
      return result;
    }
  }

  return result;
}
