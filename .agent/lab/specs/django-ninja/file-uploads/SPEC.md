# File Uploads Spec — AsForm + hydrate_form Pattern

## Rule
All endpoints that receive files MUST use `AsForm[Schema]` + `File[list[UploadedFile]]` for the typed request signature, and `hydrate_form()` to reconstruct the fully-typed schema. Business schemas MUST use `UploadedFile` as the field type — never `str`.

## Context
FormData cannot send nested JSON with files in a single typed parameter. The `AsForm` wrapper solves this by dynamically generating a Form-safe version of any Schema (converting `UploadedFile` fields to `str`), which Ninja can parse natively. After parsing, `hydrate_form()` reconstructs the real schema, resolves file tokens, and validates completeness.

---

## Pattern Overview

```
Frontend (buildApiPayload):
  data  = '{"name":"Juan","dni":"file_abc123"}'   ← token string
  files = [ File(name="file_abc123___dni.jpg") ]  ← binary with token in name

Backend (endpoint):
  data: Form[AsForm[DocumentoSchema]]  ← Ninja parses: name:str, dni:str
  files: File[list[UploadedFile]]      ← Ninja parses: array of binaries
       ↓
  hydrate_form(data, files, DocumentoSchema)
       ↓
  DocumentoSchema(name="Juan", dni=UploadedFile) ✅
```

---

## ✅ REQUIRED

### Endpoint Signature
```python
from ninja import Router, Form, File
from ninja.files import UploadedFile
from core.types import AsForm, hydrate_form
from core.responses import ApiResponse, success_response

@router.post("/", response=ApiResponse[DocumentoOut])
def crear_documento(
    request,
    data:  Form[AsForm[DocumentoSchemaIn]],
    files: File[list[UploadedFile]],
):
    payload = hydrate_form(data, files, DocumentoSchemaIn)
    ...
```

### Business Schema
```python
from django.core.files.uploadedfile import UploadedFile
from core.types import BaseSchema

class DocumentoSchemaIn(BaseSchema):
    name: str          = Field(..., description="Nombre del titular")
    dni:  UploadedFile = Field(..., description="Foto del DNI")
```

- File fields MUST be declared as `UploadedFile` in the business schema.
- All schemas MUST inherit from `BaseSchema`.
- `asForm[Schema]` is auto-generated at runtime and cached — never define it manually.

---

## hydrate_form — Built-in Validations

`hydrate_form(data, files, TargetSchema)` performs these validations before returning:

| Check | Error |
|-------|-------|
| File name doesn't contain `___` | `400` — Invalid file name format |
| JSON references token not in files | `400` — Broken file reference: token not found |
| File field receives non-string value | `400` — Field must be a token string |
| Files sent but not referenced by any field | `400` — Orphan files detected |
| Pydantic schema validation fails | `422` — handled by global exception handler |

---

## Null/Blank Cross-Stack Contract

When a Schema field is optional, the corresponding Django model field MUST match:

| Schema | Model | DB |
|--------|-------|-----|
| `campo: str` | `campo = CharField()` | `NOT NULL` |
| `campo: str \| None = None` | `campo = CharField(null=True, blank=True)` | `NULL` |
| `campo: UploadedFile` | `campo = FileField()` | `NOT NULL` |
| `campo: UploadedFile \| None = None` | `campo = FileField(null=True, blank=True)` | `NULL` |

---

## ❌ FORBIDDEN

| Pattern | Why |
|---------|-----|
| `dni: str` in business schema | Business schemas must use `UploadedFile` for files |
| `request.POST.get("data")` manually | Use `Form[AsForm[Schema]]` — fully typed |
| `parse_form_json(...)` | Deprecated — use `hydrate_form` |
| `extract_and_hydrate_payload(...)` | Deprecated — use typed endpoint signature |
| `file_uuid1`, `file_uuid2` as FormData keys | Use single `files` array with token in filename |
| Endpoint without `hydrate_form` | `AsForm` alone doesn't resolve tokens |

---

## Deprecated Patterns

| Deprecated | Replacement |
|------------|-------------|
| `hydrate_and_clean_payload(request)` | `BaseSchema` (empty → None) + `hydrate_form` (files) |
| `parse_form_json(data, files, Schema)` | `Form[AsForm[Schema]]` + `hydrate_form` |
| `extract_and_hydrate_payload(request)` | Typed endpoint: `data: Form[AsForm[T]]` |
| Individual file keys `file_uuid1` | `files: File[list[UploadedFile]]` array |

---

## Decision Log
- v1.0: Adopted `AsForm` + `hydrate_form` pattern to enable fully-typed file endpoints in Ninja.
- v1.0: `hydrate_form` owns all file validation: broken refs, orphans, format errors.
- v1.0: Deprecated manual `request.POST.get("data")` approach.
- v1.0: Cross-stack null/blank contract established for DB homogeneity.

## See Also
- [IO.md](./IO.md) — Type signatures and import map
- [EXAMPLES.md](./EXAMPLES.md) — Full endpoint + schema + frontend example
- [Shared: Django API Format](../../shared/django-api-format.md)
- [core/types.py](../../../../django-ninja-extra/core/types.py) — AsForm, hydrate_form, BaseSchema source
