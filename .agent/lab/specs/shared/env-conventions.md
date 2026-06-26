# Environment Variable Conventions

## Rule
All environment variables MUST follow the naming conventions below. Feature code MUST NOT access `process.env` directly — use the typed getter pattern.

## Naming Conventions

### ✅ REQUIRED: Namespace Prefixes

| Namespace | Purpose | Example |
|-----------|---------|---------|
| `NEXT_PUBLIC_` | Client-safe variables | `NEXT_PUBLIC_API_URL` |
| `INTERNAL_` | Server-only secrets | `INTERNAL_SECRET_KEY` |
| `TEST_` | Test-only overrides | `TEST_UUID_FORCE_MANUAL` |

### Variable Naming Pattern

```typescript
// Uppercase with underscores
NEXT_PUBLIC_API_URL
INTERNAL_STRIPE_SECRET
TEST_UUID_FORCE_MANUAL

// ❌ FORBIDDEN: camelCase or lowercase
nextPublicApiUrl    // Never
api_url             // Never
```

## Typed Getters Pattern

### ✅ REQUIRED: Use Typed Getters

```typescript
// src/config/env.ts
import { z } from "zod";

const envSchema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url(),
  NEXT_PUBLIC_IS_TEST_UUID: z
    .string()
    .transform((v) => v === "true")
    .default("false"),
  INTERNAL_STRIPE_SECRET: z.string().optional(),
});

const parsed = envSchema.safeParse(process.env);

if (!parsed.success) {
  throw new Error(`Invalid env: ${parsed.error.flatten().fieldErrors}`);
}

export const env = parsed.data;
```

### ✅ REQUIRED: Import from Config, Not `process.env`

```typescript
// ❌ FORBIDDEN: Direct process.env access
const apiUrl = process.env.NEXT_PUBLIC_API_URL;

// ✅ CORRECT: Use typed config
import { env } from "@/config/env";
const apiUrl = env.NEXT_PUBLIC_API_URL;
```

## Test UUID Flag

The `NEXT_PUBLIC_IS_TEST_UUID` flag controls UUID generation behavior:

```typescript
// When "true": Use manual UUID fallback (for HTTP environments without crypto)
// When "false" or unset: Use crypto.randomUUID()

export const shouldUseManualUUID = env.NEXT_PUBLIC_IS_TEST_UUID;
```

### When to Use Test UUID

- **Local development without backend**: Set `NEXT_PUBLIC_IS_TEST_UUID=true`
- **CI environments**: Set based on whether `crypto.randomUUID()` is available
- **Production**: Always `false` (use native crypto)

## Environment File Priority

```
.env.local           → Local overrides (gitignored)
.env.development     → Dev defaults
.env.production      → Production defaults
```

## ❌ FORBIDDEN

| Pattern | Why |
|---------|-----|
| `process.env.NEXT_PUBLIC_*` in feature code | No validation, no type safety |
| `process.env.*` without `NEXT_PUBLIC_` prefix for client vars | Client bundle exposure |
| Storing secrets in `NEXT_PUBLIC_*` | Publicly visible in client bundle |
| Default exports from env config | Harder to tree-shake |

## See Also
- [Spec: Forms](../../nextjs/forms/SPEC.md) — UUID generation in payload strategy
- [Knowledge: Next.js Environment Variables
