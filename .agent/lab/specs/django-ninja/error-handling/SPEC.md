# Error Handling Spec

## Rule
All API errors MUST return a consistent `ErrorResponse` schema with `message`, `code`, and optional `field_errors`. Domain exceptions MUST be converted to HTTP responses via custom `@exception_handler` decorators on the `NinjaAPI`.

## Context
Without a unified exception strategy, Django raises different HTTP error pages (403, 404, 500) with HTML bodies. Ninja's `api.add_exception_handler()` maps domain exceptions to structured JSON responses.

---

## Exception Hierarchy

### ✅ REQUIRED

```python
class AppException(Exception):
    """Base exception for all domain errors."""
    status_code: int = 500
    message: str = "An unexpected error occurred"
    code: str = "INTERNAL_ERROR"

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
```

### ❌ FORBIDDEN
- Raising raw Django HTTP exceptions (`Http404`, `PermissionDenied`) in services
- Returning error responses directly from endpoints (use exceptions instead)
- Catching and re-raising exceptions without preserving the original type

---

## Exception Handler Registration

### ✅ REQUIRED

```python
from ninja import NinjaAPI

api = NinjaAPI()

@api.exception_handler(AppException)
def handle_app_exception(request, exc: AppException):
    return api.create_response(
        request,
        {
            "message": exc.message,
            "code": exc.code,
            "field_errors": getattr(exc, "field_errors", None),
        },
        status=exc.status_code,
    )
```

### ❌ FORBIDDEN
- Using the default Django HTML error pages in production
- Returning raw strings as error responses (must be JSON with the ErrorResponse schema)
- Handler that re-raises unhandled exceptions instead of catching them

---

## Error Response Schema

### ✅ REQUIRED

```python
from ninja import Schema

class ErrorResponse(Schema):
    message: str
    code: str
    field_errors: dict[str, list[str]] | None = None
```

### ❌ FORBIDDEN
- Custom error shapes that don't include `message` and `code`
- Returning the exception's `str()` directly as the message without sanitization

---

## Validation Errors

### ✅ REQUIRED
- Use Pydantic's `ValidationError` for request body validation (handled automatically by Ninja)
- Custom domain validation should raise `ValidationError` with `field_errors` populated
- Field errors use snake_case keys matching the schema field names

### ❌ FORBIDDEN
- Returning 400 for validation errors (correct status is 422)
- Mixing field error keys (some camelCase, some snake_case)

---

## Decision Log
- **v1.0**: Initial spec — adopted AppException hierarchy with `message`, `code`, `field_errors`
- **v1.0**: Status codes follow RFC 7807 conventions (404 for not found, 422 for validation, 403 for auth)
