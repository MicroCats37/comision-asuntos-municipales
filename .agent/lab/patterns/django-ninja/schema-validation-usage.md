# Django Ninja: Schema Validation Usage

## Context
Separate Input and Output schemas to keep request validation and response serialization as distinct contracts. This allows the API to evolve independently on each side.

## Recipe
```python
from ninja import Schema
from pydantic import Field
from decimal import Decimal
from datetime import datetime

# --- INPUT SCHEMAS ---

class ProductCreate(Schema):
    name: str = Field(..., min_length=1, max_length=200)
    price: Decimal = Field(..., gt=0)
    category: str

class ProductUpdate(Schema):
    name: str | None = Field(None, min_length=1, max_length=200)
    price: Decimal | None = Field(None, gt=0)
    category: str | None = None

class ProductFilters(Schema):
    category: str | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    search: str | None = None

# --- OUTPUT SCHEMAS ---

class ProductResponse(Schema):
    id: int
    name: str
    price: Decimal
    category: str
    created_at: datetime
    updated_at: datetime | None = None

class ProductListResponse(Schema):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
```

## Why This Way
Input schemas use `Field(...)` constraints for validation. Output schemas include all fields the client may need. Keeping them separate prevents accidental exposure of internal fields and allows different validation rules on input vs output.

## See Also
- [Knowledge: Schemas](../../knowledge/django-ninja/schemas.md)
- [Spec: API Structure](../../specs/django-ninja/api-structure/SPEC.md)
