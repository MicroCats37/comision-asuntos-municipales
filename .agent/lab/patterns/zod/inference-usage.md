# Zod: TypeScript Type Inference

## Context
Allows the frontend to know exactly what kind of data is returned by a Server Action or an Axios request based solely on the validation schema.

## Recipe
```typescript
import { z } from 'zod';

const UserSchema = z.object({
  id: z.string().uuid(),
  username: z.string().min(3),
  age: z.coerce.number(),
});

// Infer output type (after transforms)
type User = z.infer<typeof UserSchema>; 
// Resulting type: { id: string, username: string, age: number }

// Infer input type (what we accept - before transforms)
type UserInput = z.input<typeof UserSchema>;
// Resulting type: { id: string, username: string, age: string | number }
```

## Why This Way
The schema is the single source of truth for both runtime validation and TypeScript types. This eliminates manual interface duplication and ensures types stay synchronized with validation rules.

## See Also
- [Knowledge: Type Inference](../../knowledge/zod/inference.md)
- [Spec: Forms IO](../../specs/nextjs/forms/IO.md)
