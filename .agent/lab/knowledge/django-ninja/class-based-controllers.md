# Django Ninja: Class-Based Controllers

> **PRIMARY STANDARD** — Use `django-ninja-extra` `@api_controller` for all new endpoints.

## Overview

Class-based controllers (`@api_controller`) from `django-ninja-extra` provide a structured, OOP approach to organizing API endpoints. They support constructor dependency injection, route-level and controller-level permissions, and produce cleaner codebases at scale.

## Key Concepts

- **`@api_controller`**: Decorator that turns a class into a controller. Unlike functional routers, controllers can hold state via `__init__`.
- **`@route.get()`, `@route.post()`, etc.**: Route decorators inside controllers (note: NOT `http_get`, `http_post` — those are from NinjaExtraAPI).
- **Constructor injection**: Services are injected once per controller instance, not per-request.
- **Permission stacking**: Permissions can be defined at controller level (default) or overridden per-route.

## Why Class-Based Over Functional Routers?

| Aspect | Functional Routers | Class Controllers |
|--------|---------------------|-------------------|
| DI Pattern | `Depends()` per-request | Constructor injection |
| State | Stateless (preferred) | Can hold request-scoped state |
| Permissions | Per-route only | Controller + route level |
| Code organization | Scattered across functions | Grouped by domain |
| Scalability | Good for simple APIs | Better for complex domains |

## Controller Anatomy

```python
from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated, AllowAny
from ninja import Schema

@api_controller("/users", tags=['Users'], permissions=[AllowAny])
class UserController:
    
    @route.get("/{user_id}", response=UserSchema)
    def get_user(self, user_id: int) -> User:
        """Retrieve a user by ID."""
        return User.objects.get(id=user_id)
    
    @route.post("/", response=UserSchema)
    def create_user(self, data: UserCreateSchema) -> User:
        """Create a new user."""
        return User.objects.create(**data.dict())
    
    @route.delete("/{user_id}")
    def delete_user(self, user_id: int) -> None:
        """Delete a user."""
        User.objects.get(id=user_id).delete()
        return None
```

## Route Decorators

| Decorator | HTTP Method | NinjaExtraAPI Equivalent |
|-----------|-------------|-------------------------|
| `@route.get()` | GET | `http_get` |
| `@route.post()` | POST | `http_post` |
| `@route.put()` | PUT | `http_put` |
| `@route.patch()` | PATCH | `http_patch` |
| `@route.delete()` | DELETE | `http_delete` |

## Registration

Controllers are registered with the API instance:

```python
from ninja_extra import NinjaExtraAPI
from myapp.controllers import UserController

api = NinjaExtraAPI()
api.register_controllers(UserController)
```

## Nested Controllers

Controllers can nest to share common prefixes:

```python
@api_controller("/api/v1")
class APIV1Controller:
    pass

@api_controller("/users", tags=['Users'])
class UserController(APIV1Controller):
    """Routes become /api/v1/users/{user_id}"""
    
    @route.get("/{user_id}")
    def get_user(self, user_id: int):
        return {"id": user_id}
```

## See Also

- [Pattern: Class Controller Usage](../../patterns/django-ninja/class-controller-usage.md)
- [Knowledge: Constructor DI](./constructor-di.md)
- [Knowledge: Permissions](./permissions.md)
- [Knowledge: JWT Auth](./jwt-auth.md)
