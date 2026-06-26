# File Uploads — IO Contracts

## Required Imports

```python
# Endpoint
from ninja import Router, Form, File
from ninja.files import UploadedFile
from core.types import AsForm, hydrate_form
from core.responses import ApiResponse, success_response

# Schema
from django.core.files.uploadedfile import UploadedFile
from core.types import BaseSchema
from pydantic import Field
```

---

## Endpoint Signature

```python
@router.post("/", response=ApiResponse[OutSchema])
def endpoint(
    request,
    data:  Form[AsForm[InSchema]],     # Form-safe version auto-generated
    files: File[list[UploadedFile]],   # Binary array
) -> ApiResponse[OutSchema]:
    payload: InSchema = hydrate_form(data, files, InSchema)
    ...
```

---

## Schema Pattern

### Input Schema (business layer)
```python
class EntityCreateIn(BaseSchema):
    # Regular fields
    field_a: str            = Field(..., description="...")
    field_b: str | None     = Field(None, description="...")

    # File fields — always UploadedFile in business schema
    file_field: UploadedFile          = Field(..., description="...")
    optional_file: UploadedFile | None = Field(None, description="...")
```

### What AsForm generates at runtime
```python
# AsForm[EntityCreateIn] produces at runtime (never write this manually):
class EntityCreateInForm(Schema):
    field_a:       str        # unchanged
    field_b:       str | None # unchanged
    file_field:    str        # UploadedFile → str (token)
    optional_file: str | None # UploadedFile | None → str | None
```

---

## hydrate_form Signature

```python
def hydrate_form(
    form_data:     Schema,            # Parsed AsForm instance (has token strings)
    files:         list[UploadedFile],# Raw files from Ninja
    target_schema: Type[T],           # Real business schema class
) -> T:                               # Fully hydrated instance
```

---

## Frontend Contract (payload-builder.ts)

```typescript
// Input: object with File objects
const payload = {
    field_a: "value",
    file_field: fileInput.files[0],  // File object
}

// Output FormData:
//   data  = '{"field_a":"value","file_field":"file_abc123"}'
//   files = [ File(name="file_abc123___original.jpg") ]
buildApiPayload(payload)
```

---

## Type Reference

| Schema type | AsForm generates | hydrate_form expects |
|-------------|-----------------|----------------------|
| `UploadedFile` | `str` | token matching a file in array |
| `UploadedFile \| None` | `str \| None` | token or None |
| `str` | `str` | unchanged |
| `str \| None` | `str \| None` | None if blank |
| `int`, `float`, etc. | unchanged | unchanged |
