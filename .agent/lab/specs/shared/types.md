# Type Conventions Contract

## Rule
All Zod schemas MUST follow the `{Action}{Resource}FormSchema` naming pattern. Type inference uses the standard `z.infer<>` pattern. No manual type definitions for validated data.

## Schema Export Pattern

### ✅ REQUIRED: Two Exports Per Schema File

```typescript
// features/products/schemas/product.schema.ts
import { z } from "zod";

export const CreateProductFormSchema = z.object({
  name: z.string().min(1, "Name is required"),
  price: z.number().positive("Price must be positive"),
  category: z.string().optional(),
});

export type CreateProductData = z.infer<typeof CreateProductFormSchema>;

export const UpdateProductFormSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).optional(),
  price: z.number().positive().optional(),
});

export type UpdateProductData = z.infer<typeof UpdateProductFormSchema>;
```

## Type Inference Pattern

```typescript
// Always use z.infer for validated data types
import { CreateProductFormSchema, type CreateProductData } from "../schemas";

function submitProduct(data: CreateProductData) {
  // data is fully typed from the schema
  mutate(data);
}
```

## Schema Composition

### ✅ REQUIRED: Compose for Reuse

```typescript
// Base fields shared across operations
const BaseProductSchema = z.object({
  name: z.string().min(1),
  price: z.number().positive(),
});

// Extend for create (all required)
export const CreateProductFormSchema = BaseProductSchema;

// Extend for update (all optional)
export const UpdateProductFormSchema = BaseProductSchema.partial();
```

## Shared Type Locations

| Type | Location | Export |
|------|----------|--------|
| `ApiResponse<T>` | `src/shared/types/api.types.ts` | Named export |
| `PaginatedResult<T>` | `src/shared/types/pagination.types.ts` | Named export |
| Form data types | `features/{domain}/schemas/` | Inline `z.infer` |

## React Component Prop Types

```typescript
// ✅ REQUIRED: Explicit prop interface
interface ProductFormProps {
  initialData?: ProductResponse;
  onSubmit: (data: CreateProductData) => void;
  isLoading?: boolean;
}

// ❌ FORBIDDEN: Inline types in function signature
function ProductForm({ initialData, onSubmit }: { initialData?: any }) {
```

## Generic Type Patterns

```typescript
// ✅ Use generic constraints
function useApiQuery<TData, TError = ApiError>(
  queryKey: string[],
  fetcher: () => Promise<TData>
): UseQueryResult<TData, TError>

// ❌ Avoid any
function useApiQuery(queryKey: string[], fetcher: any): any
```

## ❌ FORBIDDEN

| Pattern | Why |
|---------|-----|
| `z.infer<typeof SomeSchema> & { extra: string }` | Mixes inference with manual types |
| Manual type definitions for form data | Duplicates Zod, loses validation linkage |
| Using `as` for type assertions on validated data | Undermines type safety |
| Default exports for schemas | Makes tree-shaking harder |

## See Also
- [Spec: Forms](../../nextjs/forms/SPEC.md) — schema conventions context
- [Spec: Project Structure](../../nextjs/project-structure/SPEC.md) — naming rules
- [Knowledge: Zod Inference](../../knowledge/zod/inference.md)
