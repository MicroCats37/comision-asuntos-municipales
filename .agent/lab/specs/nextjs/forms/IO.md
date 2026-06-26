# Forms: Inputs & Outputs

## Component API

### GenericForm Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `children` | `RenderProps` \| `ReactNode` | Yes | — | See Render Props below |
| `schema` | `ZodSchema` | Yes | — | Zod schema for validation |
| `onSubmit` | `(data: T) => Promise<void>` | Yes | — | Submit handler |
| `initialData` | `T` | No | `undefined` | Pre-populated form values |
| `isLoading` | `boolean` | No | `false` | Disables form while loading |
| `className` | `string` | No | `""` | CSS class for wrapper |
| `formSections` | `FormSection[]` | No | — | Section mode config |
| `fields` | `FormField[]` | No | — | Automatic mode config |

### Render Props (Mode 1 — Manual)

```typescript
interface RenderProps<T extends Record<string, unknown>> {
  methods: UseFormReturn<T>;
  isSubmitting: boolean;
  onSubmit: (e: React.FormEvent) => void;
  submissionMessage: string | null;
}
```

### FormSection Config (Mode 3)

```typescript
interface FormSection {
  title?: string;
  description?: string;
  fields: FormField[];
  className?: string;
}
```

### FormField Config (Mode 2)

```typescript
interface FormField {
  name: string;
  label: string;
  type: "text" | "email" | "number" | "password" | "select" | "textarea";
  placeholder?: string;
  required?: boolean;
  options?: { label: string; value: string }[]; // for select
}
```

## Data Contracts

### Form Submission Flow

```
User clicks submit
        ↓
GenericForm validates via RHF + Zod
        ↓
If valid: onSubmit(data: T) is called
        ↓
Feature hook receives plain typed data
        ↓
buildApiPayload transforms if needed
        ↓
API call via useApiCreate/useApiUpdate
```

### Schema Type Exports

```typescript
// features/products/schemas/product.schema.ts
export const CreateProductFormSchema = z.object({
  name: z.string().min(1),
  price: z.number().positive(),
  category: z.string().optional(),
});

export type CreateProductData = z.infer<typeof CreateProductFormSchema>;
```

## Server Action Signatures

```typescript
// useApiCreate hook signature
function useApiCreate<TData, TPayload>(
  buildPayload?: (data: TData) => TPayload
): UseMutationResult<TData, ApiError, TData>;

// useApiUpdate hook signature
function useApiUpdate<TData, TPayload>(
  buildPayload?: (data: TData) => TPayload
): UseMutationResult<TData, ApiError, TData>;
```

## Error Handling Contract

All errors flow through `handleApiError` which:
1. Parses via Django Ninja → DRF → Generic REST chain
2. Applies field errors via RHF `setError`
3. Shows toast via `notify.error()`

Feature components handle **zero** raw error logic.

## See Also
- [Spec: Forms](./SPEC.md) — full spec
- [Shared: Error Handling](../shared/error-handling.md) — error contract
- [Shared: API Format](../shared/api-format.md) — payload builder
