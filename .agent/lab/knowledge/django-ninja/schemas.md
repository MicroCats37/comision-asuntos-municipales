# Django Ninja: Schemas

## Overview
Schemas are Pydantic models that define the shape of input and output data. Django Ninja uses `ninja.Schema` (a subclass of Pydantic's `BaseModel`) for request validation and response serialization.

## Key Concepts
- **Input schemas**: Validate incoming request data (path params, query params, body).
- **Output schemas**: Serialize response data to JSON.
- **Strict typing**: Use `Field()` for constraints, `validator()` for complex rules.
- **Separation**: Never use the same schema for input and output — they have different concerns.

## When to Use
For every endpoint. Schemas are the contract between client and API. Use `ninja.Schema` as the base class.

## Schema Anatomy
```python
from ninja import Schema
from pydantic import Field, field_validator

class ProductCreate(Schema):
    name: str = Field(..., min_length=1, max_length=200)
    price: Decimal = Field(..., gt=0)
    category: str

    @field_validator("category")
    @classmethod
    def category_upper(cls, v: str) -> str:
        return v.upper()

class ProductResponse(Schema):
    id: int
    name: str
    price: Decimal
    category: str
    created_at: datetime
```

## See Also
- [Pattern: Schema Validation Usage](../../patterns/django-ninja/schema-validation-usage.md)
- [Spec: API Structure](../../specs/django-ninja/api-structure/SPEC.md)
