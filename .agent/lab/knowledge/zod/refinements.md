# Zod: Refinements & Logic

## What is it
Applying custom validation rules (like cross-field comparisons) that go beyond standard Zod types.

## Golden Rules
- ✅ DO: Use `.refine()` for simple comparisons (e.g., password vs confirmation).
- ✅ DO: Use `.superRefine()` when you need to assign errors to specific fields in a complex object.
- ❌ DON'T: Overcomplicate schemas; try simple types like `.min()` or `.email()` first.

## Canonical Code

```typescript
const PasswordSchema = z.object({
  password: z.string().min(8),
  confirm: z.string(),
}).refine((data) => data.password === data.confirm, {
  message: "Passwords don't match",
  path: ["confirm"],
});

// Async refinements (e.g., checking uniqueness)
const UsernameSchema = z.string().refine(async (val) => {
  return await checkIsUnique(val);
}, "Username already taken");
```

## Gotchas
- Async refinements only run when using `.parseAsync()` or `.safeParseAsync()`. Standard `.parse()` will throw an error with async rules.