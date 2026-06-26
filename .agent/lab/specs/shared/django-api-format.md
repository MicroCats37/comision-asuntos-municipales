# Django API Response Format Contract

## Rule
All Django Ninja API responses MUST be wrapped in the `ApiResponse[T]` or `PaginatedApiResponse[T]` generic envelopes. All Ninja/Pydantic schemas MUST use `pydantic.Field(..., description="...")` on every attribute and MUST inherit from `BaseSchema`.

## Context
This contract standardizes responses across the full stack. Next.js and frontend applications expect a predictable `{ success, data, error }` shape. By enforcing `ApiResponse[T]` generics, `Field` documentation, and `BaseSchema` inheritance, we ensure strong typing, Swagger completeness, and DB homogeneity (no empty strings stored).

---

## BaseSchema — Mandatory Base for All Schemas

All project schemas MUST inherit from `core.types.BaseSchema` instead of `ninja.Schema` directly.

```python
from core.types import BaseSchema
from pydantic import Field

class ProductOut(BaseSchema):
    id:   str = Field(..., description="UUID del producto")
    name: str = Field(..., description="Nombre del producto")
```

### What BaseSchema does automatically
- Converts `""` / `"   "` → `None` before Pydantic validates (all endpoints, JSON and FormData).
- Preserves file tokens (`file_uuid`) — they are never converted to None.
- Enables `arbitrary_types_allowed` for `UploadedFile` fields.

### ❌ FORBIDDEN
```python
from ninja import Schema          # ← Never inherit from this directly
class ProductOut(Schema): ...
```

---

## Null/Blank Cross-Stack Contract

Empty strings are NEVER stored in the DB. Schema optionality MUST match model field constraints:

| Schema | Django Model | DB |
|--------|-------------|-----|
| `campo: str` | `campo = CharField()` | `NOT NULL` |
| `campo: str \| None = None` | `campo = CharField(null=True, blank=True)` | `NULL` |
| `campo: UploadedFile` | `campo = FileField()` | `NOT NULL` |
| `campo: UploadedFile \| None = None` | `campo = FileField(null=True, blank=True)` | `NULL` |

**Rule**: If a schema field is `Optional`, its model field MUST have `null=True, blank=True`. Mismatches cause `IntegrityError` at runtime.

---

## Response Shapes

### Single Resource Response

```python
from pydantic import Field
from core.types import BaseSchema
from core.responses import ApiResponse, success_response

class ProductOut(BaseSchema):
    id:   str = Field(..., description="Unique product identifier")
    name: str = Field(..., description="Name of the product")

@product_router.get("/{product_id}", response=ApiResponse[ProductOut])
def get_product(request, product_id: int):
    return success_response(product)
```

Response JSON:
```json
{
  "success": true,
  "data": { "id": "uuid", "name": "Widget" },
  "error": null
}
```

### Collection Response

```python
@product_router.get("/", response=ApiResponse[list[ProductOut]])
def list_products(request):
    return success_response(products)
```

### Paginated Response

```python
from core.responses import PaginatedApiResponse

@product_router.get("/paginated", response=PaginatedApiResponse[ProductOut])
def list_products_paginated(request, filters: ProductFilters = Depends()):
    return {
        "success": True,
        "data": items,
        "error": None,
        "meta": {
            "page": filters.page,
            "page_size": filters.page_size,
            "total": total,
            "total_pages": total_pages,
        }
    }
```

### File Upload Response

See [File Uploads Spec](../django-ninja/file-uploads/SPEC.md) for the full pattern.

---

## Status Code Conventions

| Status | When |
|--------|------|
| `200` | Successful GET, PATCH, DELETE |
| `201` | Successful POST (resource created) |
| `204` | Successful DELETE with no body |
| `400` | Bad request (file token errors, orphan files) |
| `401` | Unauthenticated |
| `403` | Permission denied |
| `404` | Resource not found |
| `409` | Conflict (duplicate resource) |
| `422` | Validation error (Pydantic) |
| `500` | Unexpected server error |

---

## ❌ FORBIDDEN

| Pattern | Why |
|---------|-----|
| Inheriting from `ninja.Schema` directly | Always use `BaseSchema` from `core.types` |
| Schemas without `pydantic.Field` descriptions | Swagger docs lack context for frontend |
| Returning naked schemas without `ApiResponse` wrapper | Breaks frontend `{ success, data, error }` contract |
| Using `response=dict` instead of a Schema | All responses must have explicit schema contracts |
| Model field `null=False` + schema `Optional` | IntegrityError at save time |
| `""` as default value in any schema field | Use `None` — empty strings are converted automatically |

---

## Deprecated Patterns

| Deprecated | Replacement |
|------------|-------------|
| `hydrate_and_clean_payload(request)` | `BaseSchema` + `hydrate_form` |
| `parse_form_json(data, files, Schema)` | `Form[AsForm[Schema]]` + `hydrate_form` |
| `extract_and_hydrate_payload(request)` | Typed endpoint `data: Form[AsForm[T]]` |
| `file_uuid1`, `file_uuid2` FormData keys | `files: File[list[UploadedFile]]` array |

---

## See Also
- [Spec: API Structure](../django-ninja/api-structure/SPEC.md)
- [Spec: File Uploads](../django-ninja/file-uploads/SPEC.md)
- [Spec: Error Handling](../django-ninja/error-handling/SPEC.md)
- [Shared: API Format](./api-format.md)
- [core/types.py source](../../../../django-ninja-extra/core/types.py)
