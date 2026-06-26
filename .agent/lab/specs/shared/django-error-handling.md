# Django Error Handling Contract

## Rule
All domain exceptions MUST extend `AppException` and be handled by a single `@api.exception_handler(AppException)` registered on the `NinjaAPI`. Error responses use the `ErrorResponse` schema with `message`, `code`, and optional `field_errors`.

## Context
This contract extends the general `error-handling.md` for Django Ninja specifically. It defines the exception hierarchy, handler registration, and the Django-specific error response shape.

---

## Exception Hierarchy

```python
class AppException(Exception):
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

---

## Handler Registration

```python
from ninja import NinjaAPI

api = NinjaAPI(urls_path="api/v1")

@api.exception_handler(AppException)
def handle_app_exception(request, exc: AppException):
    return api.create_response(
        request,
        {
            "message": exc.message,
            "code": exc.code,
            "field_errors": exc.field_errors,
        },
        status=exc.status_code,
    )
```

---

## Error Response Schema

```python
from ninja import Schema

class ErrorResponse(Schema):
    message: str
    code: str
    field_errors: dict[str, list[str]] | None = None
```

### Example Error Responses

**404 Not Found:**
```json
{
  "message": "Product 999 not found",
  "code": "PRODUCT_NOT_FOUND",
  "field_errors": null
}
```

**422 Validation Error:**
```json
{
  "message": "Validation failed",
  "code": "VALIDATION_ERROR",
  "field_errors": {
    "name": ["Field is required"],
    "price": ["Must be greater than 0"]
  }
}
```

**403 Permission Denied:**
```json
{
  "message": "Permission denied",
  "code": "PERMISSION_DENIED",
  "field_errors": null
}
```

---

## ❌ FORBIDDEN

| Pattern | Why |
|---------|-----|
| Raising Django HTTP exceptions (`Http404`, `PermissionDenied`) in services | Must use `AppException` subclasses |
| Handler that returns HTML (Django default) | Must return JSON with `ErrorResponse` schema |
| Returning unvalidated user input in error messages | Sanitize to prevent information leakage |
| Mixing exception types | All domain errors must extend `AppException` |

---

## See Also
- [Spec: Error Handling](../django-ninja/error-handling/SPEC.md)
- [Shared: Error Handling](./error-handling.md)
