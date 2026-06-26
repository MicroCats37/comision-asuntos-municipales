# Zod: Schema Composition

## What is it
Sharing and modularizing schemas using intersection (`merge`), extension (`extend`), and picking (`pick`).

## Golden Rules
- ✅ DO: Use `.merge()` to combine two distinct object schemas.
- ✅ DO: Use `.extend()` to add new fields to an existing object schema.
- ❌ DON'T: Create deep nesting without reasons; flat schemas are easier to maintain.

## Canonical Code

```typescript
const BaseSchema = z.object({ id: z.string() });

// Extension
const UserSchema = BaseSchema.extend({ name: z.string() });

// Merge
const ProfileSchema = z.object({ bio: z.string() });
const CompleteUserSchema = UserSchema.merge(ProfileSchema);
```

## Gotchas
- `.merge()` overwrites fields if they have the same name.