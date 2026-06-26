# API Structure: Inputs & Outputs

## Request Schemas

### Pagination Params
```python
from ninja import Schema
from pydantic import Field

class PaginationParams(Schema):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
```

### Product Schemas
```python
from ninja import Schema
from pydantic import Field
from decimal import Decimal
from datetime import datetime

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
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
```

## Response Schemas

### Product Response
```python
class ProductResponse(Schema):
    id: int
    name: str
    price: Decimal
    category: str
    created_at: datetime
    updated_at: datetime | None = None
```

### Paginated Response
```python
class PaginatedProductResponse(Schema):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
```

## See Also
- [Spec: API Structure](./SPEC.md)
- [Shared: Django API Format](../shared/django-api-format.md)
