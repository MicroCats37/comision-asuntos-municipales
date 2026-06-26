# Error Handling Contract

## Rule
All API errors MUST flow through the standardized parser chain and be consumed via the toast adapter. Components handle zero raw error logic.

## Error Parser Chain

```
Django Ninja HTTP Error
        ↓
    DRF Error Format
        ↓
  Generic REST Error
        ↓
  Field-level Mapping
        ↓
    RHF setError + Toast
```

### ✅ REQUIRED: Use `handleApiError`

```typescript
// All submission errors flow through this function
import { handleApiError } from "@/errors/error-handler";

// In a form's onSubmit:
onSubmit={async (data) => {
  try {
    await createProduct(data);
  } catch (error) {
    handleApiError(error);
  }
}}
```

### ✅ REQUIRED: Toast Adapter Pattern

The toast adapter is swappable. Always use the adapter, never call `toast()` directly:

```typescript
import { notify } from "@/errors/toast-adapter";

// Correct:
notify.success("Product created!");
notify.error("Failed to create product.");

// ❌ FORBIDDEN: Direct toast calls
import { toast } from "@/components/ui/use-toast";
toast({ title: "Error" }); // Never directly
```

## Field Error Application

`handleApiError` automatically:
1. Parses the error response through the chain (Django → DRF → Generic REST)
2. Extracts `fieldErrors` mapping
3. Calls RHF's `setError` for each field
4. Shows a toast with the top-level message

## API Error Shapes

### Django Ninja (source)
```typescript
{ detail: "Validation error" } | { detail: { field_name: ["msg"] } }
```

### DRF (middleware)
```typescript
{ message: string, errors: Record<string, string[]> }
```

### Generic REST (normalized)
```typescript
{ message: string, fieldErrors?: Record<string, string>, code?: string }
```

## ❌ FORBIDDEN

| Pattern | Why |
|---------|-----|
| `try/catch` with manual `setError` in components | `GenericForm` already handles this |
| Direct `toast()` calls | Must use the swappable adapter |
| Catching errors without calling `handleApiError` | Errors won't be parsed correctly |
| Re-throwing errors after catching | Breaks the error chain |

## See Also
- [Spec: Forms](../../nextjs/forms/SPEC.md) — error handling in form context
- [Knowledge: Axios Error Handling](../../knowledge/axios/error-handling.md)
