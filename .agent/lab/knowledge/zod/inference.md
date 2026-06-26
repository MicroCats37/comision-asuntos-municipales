# Zod: Type Inference (The Source of Truth)

## What is it
Zod's ability to automatically generate TypeScript types from a schema definition, eliminating the need to write interfaces manually.

## Golden Rules
- ✅ DO: Always use `z.infer<typeof schema>` to keep the code synchronized with the validation.
- ✅ DO: Differentiate between `z.input` (raw data) and `z.output`/`z.infer` (validated and transformed data).
- ❌ DON'T: Write manual interfaces for objects that already have a Zod schema.

## Canonical Code

```typescript
import { z } from 'zod';

const UserSchema = z.object({
  id: z.string().uuid(),
  username: z.string().min(3),
  age: z.coerce.number(), // Automatically transforms string -> number
});

// 1. Standard inference (output)
type User = z.infer<typeof UserSchema>; 
// Resulting type: { id: string, username: string, age: number }

// 2. Input inference (what we accept)
type UserInput = z.input<typeof UserSchema>;
// Resulting type: { id: string, username: string, age: string | number }
```

## Gotchas
- `z.infer` always returns the **output** type (after transforms). If your schema converts a string to a `Date`, `z.infer` will be `Date`, while `z.input` will be `string`.


