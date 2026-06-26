# Error Handling: Inputs & Outputs

## Exception Classes

```python
from ninja import Schema
from typing import Any

class AppException(Exception):
    """Base exception for all domain errors."""
    status_code: int = 500
    message: str = "An unexpected error occurred"
    code: str = "INTERNAL_ERROR"
    field_errors: dict[str, list[str]] | None = None

    def __init__(
        self,
        message: str | None = None,
        field_errors: dict[str, list[str]] | None = None,
    ):
        if message:
            self.message = message
        if field_errors is not None:
            self.field_errors = field_errors
        super().__init__(self.message)


class ProductNotFoundError(AppException):
    status_code = 404
    message = "Product not found"
    code = "PRODUCT_NOT_FOUND"


class ValidationError(AppException):
    status_code = 422
    message = "Validation failed"
    code = "VALIDATION_ERROR"


class PermissionDeniedError(AppException):
    status_code = 403
    message = "Permission denied"
    code = "PERMISSION_DENIED"


class ConflictError(AppException):
    status_code = 409
    message = "Resource conflict"
    code = "CONFLICT"
```

## Error Response Schema

```python
class ErrorResponse(Schema):
    message: str
    code: str
    field_errors: dict[str, list[str]] | None = None
```

## Field Error Format

```python
# Example: ValidationError with field_errors
{
    "message": "Validation failed",
    "code": "VALIDATION_ERROR",
    "field_errors": {
        "name": ["Field is required"],
        "price": ["Must be greater than 0"],
    }
}
```

## See Also
- [Spec: Error Handling](./SPEC.md)
- [Shared: Django Error Handling](../shared/django-error-handling.md)
