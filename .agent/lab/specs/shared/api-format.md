# API Response Format Contract

## Rule
All API responses MUST conform to the `ApiResponse<T>` shape. Payload builders handle the transformation from domain types to API format.

## Standard Response Shape

```typescript
// Generic REST API response
interface ApiResponse<T> {
  data: T;
  message: string;
  success: true;
}

// Error response (non-2xx)
interface ApiError {
  message: string;
  fieldErrors?: Record<string, string>;
  code?: string;
  success: false;
}
```

## Pagination Contract

```typescript
interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
  success: true;
}
```

## Payload Builder Pattern

### ✅ REQUIRED: `buildApiPayload` in Hooks

```typescript
// src/utils/payload-builder.ts
export function buildApiPayload<T extends Record<string, unknown>>(
  data: T
): T | FormData {
  const hasFiles = Object.values(data).some(
    (v) => v instanceof File || v instanceof FileList
  );

  if (!hasFiles) return data;

  const formData = new FormData();
  for (const [key, value] of Object.entries(data)) {
    if (value instanceof FileList) {
      Array.from(value).forEach((f) => formData.append(key, f));
    } else if (value !== undefined) {
      formData.append(key, value as string | Blob);
    }
  }
  return formData;
}
```

### ✅ REQUIRED: Payload Builder Lives in Hooks

```
Component onSubmit → mutate(data: T) → useApiCreate → buildApiPayload(data) → API
```

❌ FORBIDDEN: Calling `buildApiPayload` inside the form's `onSubmit`

## Schema Naming Conventions

```typescript
// Form schemas (client-side validation)
{Action}{Resource}FormSchema  →  {Action}{Resource}Data

// Examples:
CreateProductFormSchema      →  CreateProductData
UpdateUserFormSchema          →  UpdateUserData

// API request/response schemas (server contracts)
CreateProductSchema           →  CreateProductData    // POST body
ProductResponseSchema        →  ProductResponse      // GET response
```

## ❌ FORBIDDEN

| Pattern | Why |
|---------|-----|
| Returning raw FormData without checking for files | Breaks JSON endpoints |
| Building payloads in components | Wrong layer, ruins TypeScript inference |
| Using `any` for response types | Breaks type safety |
| Mixing camelCase and snake_case | Our API uses snake_case internally |

## See Also
- [Spec: Forms](../../nextjs/forms/SPEC.md) — payload strategy context
- [Spec: Project Structure](../../nextjs/project-structure/SPEC.md) — schema naming rules
