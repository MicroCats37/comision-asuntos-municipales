# Pattern: ModelControllerBase — Automatic CRUD

> **APPLICABLE TO**: `django-ninja-extra` class controllers using `ModelControllerBase` mixin.

## Use Case

Generating list, retrieve, create, update, and delete endpoints automatically for a simple Django model that requires no business logic, transactions, or service layer.

## Example: FeriadoController

```python
# modulos/alojamiento/controllers/feriado_controller.py
from ninja_extra import api_controller, route
from ninja_extra.model_conttroller import ModelControllerBase
from ninja import Schema
from pydantic import Field
from typing import List
from core.types import BaseSchema
from core.responses import ApiResponse

class FeriadoSchema(BaseSchema):
    id: int = Field(..., description="Unique identifier")
    fecha: str = Field(..., description="Date of the holiday (YYYY-MM-DD)")
    nombre: str = Field(..., description="Holiday name")
    es_recurrente: bool = Field(..., description="Repeats annually if True")
    habilitado: bool = Field(..., description="Whether the holiday is active")

@api_controller("/feriados", tags=['Feriados'])
class FeriadoController(ModelControllerBase):
    model_class = Feriado
    input_schema = FeriadoSchema
    output_schema = FeriadoSchema
    pagination_enabled = True
```

### What ModelControllerBase provides automatically

| Method | Route | Description |
|--------|-------|-------------|
| `list` | `GET /` | Paginated list of records |
| `retrieve` | `GET /{id}` | Get single record |
| `create` | `POST /` | Create new record |
| `update` | `PUT /{id}` | Full update |
| `patch` | `PATCH /{id}` | Partial update |
| `delete` | `DELETE /{id}` | Delete record |

## Project-Specific Response Wrapping

`ModelControllerBase` returns naked schemas by default. To match the project's `ApiResponse[T]` contract, you **must** wrap the output:

```python
from core.responses import success_response

@api_controller("/feriados", tags=['Feriados'])
class FeriadoController(ModelControllerBase):
    # ... configuration ...

    @route.get("/", response=ApiResponse[List[FeriadoSchema]])
    def list_feriados(self, **kwargs):
        return success_response(super().list(**kwargs))

    @route.get("/{feriado_id}", response=ApiResponse[FeriadoSchema])
    def get_feriado(self, **kwargs):
        return success_response(super().retrieve(**kwargs))
```

Alternatively, override `get_output_schema` to auto-wrap:

```python
def get_output_schema(self):
    return ApiResponse[self.input_schema]
```

---

## ⚠️ WARNING — Not Suitable for This Project's Core Models

`ModelControllerBase` is designed for **simple, flat CRUD** resources. It is **NOT appropriate** for the following alojamiento models:

### ❌ ReservaBungalows (Reserva Maestra)

- Links to `OrdenDeCobro` (finanzas domain)
- Links to `Usuario` (identidad domain)
- Requires business logic: noche count, vencida check, orden relationship
- Has `HistoricalRecords` audit — creation/update must preserve history via service, not raw `save()`
- **Use**: Repository + Service pattern with explicit endpoints

### ❌ BungalowReservado

- Nested under `ReservaBungalows` — creating requires setting FK from parent context
- Contains JSON `desglose_noches` and `snapshot_huespedes` — demands business logic to build
- Subtotal calculation involves tariff lookup and privilege application
- **Use**: Explicit endpoint on `ReservaBungalowsController` with service orchestration

### ❌ NocheBungalow

- No physical `esta_ocupada` field — state is **computed dynamically** via `.orden.esta_pagada`
- `.orden` and `.estado` are `@property` methods, not stored fields
- Automatic CRUD would bypass the dynamic state computation entirely
- **Use**: Custom endpoint with service that resolves nightly state at query time

### ❌ Huesped

- `estado_tiempo_real` is a computed property that queries `ControlAcceso` log in real time
- Depends on `ReservaBungalows` dates and cross-module `ControlAcceso` data
- **Use**: Custom endpoint with selector that computes real-time state

### ✅ Simple Admin CRUD Candidates

The following models **could** use `ModelControllerBase` with response wrapping:

| Model | Reason it fits |
|-------|----------------|
| `Feriado` | Flat fields, no relations, no computed state |
| `Bungalow` (basic fields) | If no tariff/availability logic needed |
| `Parameters` (if simple key-value) | Flat, no cross-domain links |

---

## Key Limitations

| Limitation | Impact |
|------------|--------|
| No business logic hook | Cannot inject services for tariff calculation, availability checks, etc. |
| Naked schema response | Does not return `ApiResponse[T]` — frontend expects `{ success, data, error }` |
| No nested handling | Cannot handle `BungalowReservado` creation nested under `ReservaBungalows` |
| No transaction awareness | Cannot coordinate multiple model saves in a single transaction |
| No authorization customization | Permissions are coarse-grained; complex resource policies require explicit endpoints |

---

## See Also

- [Pattern: Class Controller Usage](./class-controller-usage.md) — Primary standard for this project
- [Pattern: Constructor DI Usage](./constructor-di-usage.md) — Service injection
- [Spec: Django API Format Contract](../../specs/shared/django-api-format.md) — `ApiResponse[T]` mandatory wrapping