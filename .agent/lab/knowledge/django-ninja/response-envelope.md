# Response Envelope Standard

## Rule
All API responses from Django Ninja endpoints MUST use the standard `ApiResponse` envelope to ensure consistent client experience.

## Overview

The response envelope provides a predictable structure for all API responses:

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | `true` for successful responses, `false` for errors |
| `data` | `Any` | Response payload (null on error) |
| `error` | `ErrorDetail \| null` | Error details (null on success) |
| `meta` | `PaginationMeta \| null` | Pagination info (only for paginated responses) |

---

## Schemas

### `ApiResponse`
```python
from typing import Any
from ninja import Schema

class ErrorDetail(Schema):
    code: str                          # e.g. "VALIDATION_ERROR"
    message: str                       # Human-readable message
    details: dict | None = None        # Field errors, extra context

class ApiResponse(Schema):
    success: bool
    data: Any | None = None
    error: ErrorDetail | None = None
```

### `PaginatedApiResponse`
```python
class PaginationMeta(Schema):
    page: int
    page_size: int
    total: int
    total_pages: int

class PaginatedApiResponse(ApiResponse):
    meta: PaginationMeta | None = None
```

---

## Error Codes

| Code | HTTP Status | When Used |
|------|-------------|-----------|
| `NOT_FOUND` | 404 | Resource does not exist |
| `VALIDATION_ERROR` | 422 | Pydantic/Django validation failed |
| `PERMISSION_DENIED` | 403 | User lacks required permission |
| `CONFLICT` | 409 | Resource already exists (e.g., duplicate email) |
| `BUSINESS_ERROR` | 400 | Business rule violation |
| `INTERNAL_ERROR` | 500 | Unexpected server error |
| `HTTP_ERROR` | varies | HTTP error from external service |

---

## Helper Functions

### `success_response(data)`
Returns a success envelope with the provided data.

```python
from django_ninja_extra.core.responses import success_response

# In a controller:
@route.get("/users/{user_id}")
def get_user(request, user_id: int):
    user = user_service.get_by_id(user_id)
    return success_response(user)
```

Response:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "john",
    "email": "john@example.com"
  },
  "error": null
}
```

### `error_response(code, message, details=None, status=400)`
Returns an error envelope with the specified error code.

```python
from django_ninja_extra.core.responses import error_response

# In a controller or exception handler:
@route.get("/users/{user_id}")
def get_user(request, user_id: int):
    user = user_service.get_by_id(user_id)
    if not user:
        return error_response(
            code="NOT_FOUND",
            message="User not found",
            details={"user_id": user_id},
            status=404
        )
    return success_response(user)
```

Response:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "NOT_FOUND",
    "message": "User not found",
    "details": {"user_id": 123}
  }
}
```

---

## Usage in Controllers

### Basic Success Response
```python
from django_ninja_extra.core.responses import success_response

@api_controller("/users")
class UserController:
    @route.get("/{user_id}")
    def get_user(self, user_id: int):
        user = self.user_service.get_by_id(user_id)
        return success_response(user)
```

### Paginated Response
```python
from django_ninja_extra.core.responses import success_response

@api_controller("/users")
class UserController:
    @route.get("/")
    def list_users(self, page: int = 1, page_size: int = 20):
        paginated = self.user_service.list(page=page, page_size=page_size)
        return success_response({
            "items": paginated.items,
            "meta": {
                "page": paginated.page,
                "page_size": paginated.page_size,
                "total": paginated.total,
                "total_pages": paginated.total_pages,
            }
        })
```

### Error Response
```python
from django_ninja_extra.core.responses import success_response, error_response

@api_controller("/users")
class UserController:
    @route.post("/")
    def create_user(self, data: UserCreate):
        if self.user_service.email_exists(data.email):
            return error_response(
                code="CONFLICT",
                message="Email already registered",
                details={"email": data.email},
                status=409
            )
        user = self.user_service.create(data)
        return success_response(user)
```

---

## Usage in Exception Handlers

Exception handlers automatically return the envelope using `error_response`:

```python
from django_ninja_extra.core.responses import error_response

@api.exception_handler(ObjectDoesNotExist)
def on_object_not_found(request, exc):
    body, status = error_response(
        code="NOT_FOUND",
        message="The requested resource does not exist"
    )
    return api.create_response(request, body, status=status)
```

---

## Client-Side Usage

### JavaScript/TypeScript
```typescript
interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: ErrorDetail | null;
}

interface ErrorDetail {
  code: string;
  message: string;
  details: Record<string, unknown> | null;
}

async function fetchUser(userId: number) {
  const response = await fetch(`/api/users/${userId}`);
  const envelope: ApiResponse<User> = await response.json();
  
  if (!envelope.success) {
    throw new Error(`${envelope.error?.code}: ${envelope.error?.message}`);
  }
  
  return envelope.data;
}
```

### Python
```python
import requests

def fetch_user(user_id: int) -> dict:
    response = requests.get(f"/api/users/{user_id}")
    envelope = response.json()
    
    if not envelope["success"]:
        error = envelope["error"]
        raise RuntimeError(f"{error['code']}: {error['message']}")
    
    return envelope["data"]
```

---

## See Also
- [Error Handling Spec](../specs/django-ninja/error-handling/SPEC.md)
- [Bounded Context Spec](../specs/django-ninja/bounded-context/SPEC.md)
