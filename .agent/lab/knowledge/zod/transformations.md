# Zod: Transformations & Mapping

## What is it
The ability to transform incoming data into a clean, normalized format during validation.

## Golden Rules
- ✅ DO: Use `.transform()` to sanitize data (e.g., trim strings, normalize casing).
- ✅ DO: Use `.pipe()` to chain schemas and ensure the output of a transform is also validated.
- ❌ DON'T: Put heavy business logic inside transformations; keep them focused on data normalization.

## Canonical Code

```typescript
const TrimmedString = z.string().transform((val) => val.trim());

const PriceSchema = z.string()
  .transform((val) => parseFloat(val))
  .pipe(z.number().positive()); // Ensure transformed value is a positive number
```

## Gotchas
- Transformations only run upon successful validation of the previous step.