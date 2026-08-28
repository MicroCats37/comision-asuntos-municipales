/**
 * Build Update Payload Helper
 *
 * Constructs a partial-update payload from form values, initial data, and a Zod schema.
 *
 * Rules:
 * - Omits `undefined` values (field not touched)
 * - For fields with metadata `kind: "file"`:
 *   - string URL value → omitted (no change)
 *   - File value → included (replace)
 *   - null value → included (clear/remove)
 *   - undefined → omitted (no change)
 * - For other fields: included if !== undefined (no deep equality in this version)
 *
 * Zod v4 note: We use a Symbol-keyed property to detect file-kind schemas.
 * See `imageField.ts` for the metadata convention.
 */

import type { z } from "zod";
import { isFileKindSchema } from "./imageField";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ZodTypeAny = z.ZodType<any, any, any>;

// ── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Recursively walk a Zod schema's shape() to find subschemas.
 * Returns a flat list of [key, schema] pairs for object schemas.
 */
function walkSchemaShape(
  schema: ZodTypeAny,
  prefix: string = "",
): Array<[string, ZodTypeAny]> {
  const entries: Array<[string, ZodTypeAny]> = [];

  // Handle ZodObject
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const def = (schema as any)._def;
  const shape = def?.shape;
  if (typeof shape === "function") {
    try {
      const resolved = shape();
      if (resolved && typeof resolved === "object") {
        for (const [key, fieldSchema] of Object.entries(resolved)) {
          entries.push([
            prefix ? `${prefix}.${key}` : key,
            fieldSchema as ZodTypeAny,
          ]);
          entries.push(
            ...walkSchemaShape(
              fieldSchema as ZodTypeAny,
              prefix ? `${prefix}.${key}` : key,
            ),
          );
        }
      }
    } catch {
      // shape() may throw for some schema types
    }
    return entries;
  }

  if (shape && typeof shape === "object") {
    for (const [key, fieldSchema] of Object.entries(shape)) {
      entries.push([
        prefix ? `${prefix}.${key}` : key,
        fieldSchema as ZodTypeAny,
      ]);
      entries.push(
        ...walkSchemaShape(
          fieldSchema as ZodTypeAny,
          prefix ? `${prefix}.${key}` : key,
        ),
      );
    }
    return entries;
  }

  // Handle ZodOptional / ZodNullable — try unwrap
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const unwrap = (def as any)?.unwrap;
  if (typeof unwrap === "function") {
    try {
      entries.push(...walkSchemaShape(unwrap(), prefix));
    } catch {
      // ignore
    }
  }

  // Handle discriminated unions — try options
  const options = def?.options;
  if (Array.isArray(options)) {
    for (const option of options) {
      entries.push(...walkSchemaShape(option, prefix));
    }
  }

  return entries;
}

/**
 * Check if a schema is a "file kind" schema (has our Symbol metadata attached).
 */
function isFileKind(schema: ZodTypeAny): boolean {
  return isFileKindSchema(schema);
}

// ── Main function ─────────────────────────────────────────────────────────────

export interface BuildUpdatePayloadOptions {
  /**
   * If true, only omit undefined values (include all other values).
   * If false, also omit values that equal initialData for non-file fields.
   */
  strict?: boolean;
}

/**
 * Build a partial update payload from form values + initial data + schema.
 *
 * @param values   Current form values (may include File, string URLs, null, undefined)
 * @param initialData  Original data (for comparison)
 * @param schema   Zod schema (used to identify file-kind fields)
 * @param options  Optional configuration
 */
export function buildUpdatePayload<T extends Record<string, unknown>>(
  values: T,
  initialData: Partial<T> | undefined,
  schema: z.ZodType<T>,
  options: BuildUpdatePayloadOptions = {},
): Partial<T> {
  const result: Partial<T> = {};
  const schemaEntries = walkSchemaShape(schema);

  for (const [key, value] of Object.entries(values)) {
    if (value === undefined) {
      // Always omit undefined (field not touched)
      continue;
    }

    // Find corresponding schema entry
    const schemaEntry = schemaEntries.find(([k]) => k === key);
    const fieldSchema = schemaEntry?.[1];

    if (fieldSchema && isFileKind(fieldSchema)) {
      // File-kind field handling
      if (typeof value === "string") {
        // string URL = no change, omit
        continue;
      }
      // File (replace) or null (clear) → include
      result[key as keyof T] = value as T[keyof T];
    } else {
      // Non-file field: include if defined
      result[key as keyof T] = value as T[keyof T];
    }
  }

  return result;
}
