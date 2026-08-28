/**
 * Image/File Field Helper for Zod v4
 *
 * Zod v4's .meta() getter/setter does NOT persist metadata to _def.metadata
 * (it returns undefined even after calling .meta({...})).
 * We use a Symbol-keyed property to attach file-kind metadata to schemas.
 *
 * Usage:
 *   import { imageField } from "@/lib/forms/imageField";
 *   const { schema, metadata } = imageField();
 *   // schema is ZodType<File|null|undefined>
 *   // metadata.kind === "file"
 */

import { z } from "zod";

// ── Symbol key for non-enumerable metadata attachment ─────────────────────────

const FILE_KIND_KEY = Symbol("fileKind");

// ── Public types ─────────────────────────────────────────────────────────────

export interface ImageFieldResult {
  schema: z.ZodType<File | null | undefined>;
  metadata: { kind: "file" };
}

/**
 * Check if a Zod schema represents a file field (has file-kind metadata).
 */
export function isFileKindSchema(schema: unknown): boolean {
  if (typeof schema !== "object" || schema === null) return false;
  const s = schema as Record<string | symbol, unknown>;
  return (
    FILE_KIND_KEY in s &&
    (s[FILE_KIND_KEY] as { kind: string } | undefined)?.kind === "file"
  );
}

// ── Helper ───────────────────────────────────────────────────────────────────

/**
 * Creates a Zod schema for image/file upload fields with attached metadata.
 *
 * - Accepts File (new upload)
 * - Accepts null (remove/clear existing)
 * - Accepts undefined (no change / untouched)
 *
 * Attach metadata via Symbol to avoid enumeration in JSON serialization.
 */
export function imageField(): ImageFieldResult {
  const base = z.instanceof(File).optional().nullable();
  Object.defineProperty(base, FILE_KIND_KEY, {
    value: { kind: "file" as const },
    enumerable: false,
    writable: true,
    configurable: true,
  });
  return {
    schema: base,
    metadata: { kind: "file" },
  };
}
