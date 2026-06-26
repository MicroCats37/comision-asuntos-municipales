# File Uploads — Examples

## Complete Example: Documento with DNI Photo

### Django Model
```python
# features/documentos/models.py
from django.db import models
from core.models import BaseModel

class Documento(BaseModel):
    # Required field → null=False (default)
    name = models.CharField(max_length=100)

    # Required file → null=False (default)
    dni = models.FileField(upload_to="documentos/dni/")

    # Optional field → null=True, blank=True (matches schema: str | None)
    observaciones = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Documento"
```

### Schemas
```python
# features/documentos/schemas.py
from pydantic import Field
from django.core.files.uploadedfile import UploadedFile
from core.types import BaseSchema

class DocumentoCreateIn(BaseSchema):
    name:          str            = Field(..., description="Nombre del titular del documento")
    dni:           UploadedFile   = Field(..., description="Foto del DNI (frente)")
    observaciones: str | None     = Field(None, description="Observaciones opcionales")

class DocumentoOut(BaseSchema):
    id:            str            = Field(..., description="UUID único del documento")
    name:          str            = Field(..., description="Nombre del titular")
    observaciones: str | None     = Field(None, description="Observaciones")
```

### Endpoint
```python
# features/documentos/presentation/routers.py
from ninja import Router, Form, File
from ninja.files import UploadedFile
from core.types import AsForm, hydrate_form
from core.responses import ApiResponse, success_response, error_response
from ..schemas import DocumentoCreateIn, DocumentoOut
from ..models import Documento

router = Router(tags=["Documentos"])

@router.post("/", response=ApiResponse[DocumentoOut])
def crear_documento(
    request,
    data:  Form[AsForm[DocumentoCreateIn]],
    files: File[list[UploadedFile]],
):
    # Hydrate: token strings → UploadedFile, "" → None, validate tokens
    payload = hydrate_form(data, files, DocumentoCreateIn)

    doc = Documento.objects.create(
        name=payload.name,
        dni=payload.dni,                    # UploadedFile → Django saves to disk
        observaciones=payload.observaciones, # None if blank was sent
    )

    return success_response(DocumentoOut(
        id=str(doc.id),
        name=doc.name,
        observaciones=doc.observaciones,
    ))
```

### Frontend (Next.js)
```typescript
// next/src/features/documentos/api.ts
import { buildApiPayload } from "@/utils/payload-builder";
import api from "@/lib/axios";

export async function crearDocumento(data: {
    name: string;
    dni: File;
    observaciones?: string;
}) {
    const response = await api.post("/documentos/", buildApiPayload(data));
    return response.data; // ApiResponse<DocumentoOut>
}
```

### What travels over the wire
```
POST /api/v1/documentos/
Content-Type: multipart/form-data

data  = '{"name":"Juan Pérez","dni":"file_abc123","observaciones":""}'
files = [ File(name="file_abc123___dni_frente.jpg", type="image/jpeg") ]
```

### After hydrate_form
```python
payload.name          # → "Juan Pérez"
payload.dni           # → InMemoryUploadedFile(name="dni_frente.jpg")  ← clean name
payload.observaciones # → None  ← "" was sanitized to None by BaseSchema
```

### Swagger UI shows
```
POST /documentos/
  data:  string (Form)  ← JSON string with tokens
  files: array (File)   ← binary array

Response 200:
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Juan Pérez",
    "observaciones": null
  },
  "error": null
}
```

---

## Error Cases

### Missing file (token in JSON but no binary sent)
```
400 Bad Request
{
  "success": false,
  "data": null,
  "error": {
    "code": "BAD_REQUEST",
    "message": "Referencia de archivo rota: el campo 'dni' referencia el token 'file_abc123' pero no se encontró en los archivos enviados."
  }
}
```

### Empty required field ("" sent for name)
```
422 Unprocessable Entity  ← Pydantic catches: None is not a valid str
{
  "name": "campo requerido"
}
```

### Orphan file (file sent but not referenced)
```
400 Bad Request
{
  "success": false,
  "data": null,
  "error": {
    "code": "BAD_REQUEST",
    "message": "Se enviaron archivos que no están referenciados en ningún campo: file_xyz789."
  }
}
```
