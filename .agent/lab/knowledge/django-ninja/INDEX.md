# Django Ninja Knowledge Index

## PRIMARY Standard — django-ninja-extra & django-ninja-jwt

> **NEW:** Use `django-ninja-extra` for class-based controllers and constructor DI. Use `django-ninja-jwt` for authentication.

### Class Controllers & DI
| Doc | Topic | When to Read |
|-----|-------|-------------|
| [hexagonal-architecture.md](./hexagonal-architecture.md) | Hexagonal Architecture | **PRIMARY** — DDD-lite layer flow |
| [class-based-controllers.md](./class-based-controllers.md) | Class Controllers | **PRIMARY** — `@api_controller` with routing |
| [constructor-di.md](./constructor-di.md) | Constructor DI | **PRIMARY** — `@inject` from `injector` |
| [permissions.md](./permissions.md) | Permissions | **PRIMARY** — Permission arrays |
| [jwt-auth.md](./jwt-auth.md) | JWT Auth | **PRIMARY** — `django-ninja-jwt` setup |
| [response-envelope.md](./response-envelope.md) | Response Envelope | **PRIMARY** — `ApiResponse` standard |

### Service Architecture
| Doc | Topic | When to Read |
|-----|-------|-------------|
| [services.md](./services.md) | Service Layer | Business logic separation |
| [selectors.md](./selectors.md) | Selector Layer | Data retrieval patterns |
| [schemas.md](./schemas.md) | Pydantic Schemas | Input/Output validation |

## Alternative/Simple APIs

> These documents describe the standard Ninja approach. Use only for simple endpoints or when integrating with non-Extra code.

| Doc | Topic | When to Use |
|-----|-------|-------------|
| [routers.md](./routers.md) | Functional Routers | Legacy/simple endpoints only |
| [dependency-injection.md](./dependency-injection.md) | `Depends()` DI | Per-request injection (non-Extra) |

## Additional Topics
| Doc | Topic | When to Read |
|-----|-------|-------------|
| [testing.md](./testing.md) | TestClient | Testing endpoints |
| [async.md](./async.md) | Async Views | sync_to_async, async ORM |

## Quick Reference

### PRIMARY Standard (django-ninja-extra)
```python
from ninja_extra import api_controller, route
from injector import inject

@api_controller("/users")
class UserController:
    @inject
    def __init__(self, user_service: UserService):
        self.user_service = user_service
    
    @route.get("/{user_id}")
    def get_user(self, user_id: int):
        return self.user_service.get_by_id(user_id)
```

### JWT Authentication
```python
from ninja_jwt.controller import NinjaJWTDefaultController
from ninja_jwt.authentication import JWTAuth

api = NinjaExtraAPI()
api.register_controllers(NinjaJWTDefaultController)

@route.get("/me", auth=JWTAuth())
def get_me(self, request):
    return request.user
```

## See Also
- [Patterns: Django Ninja](../../patterns/django-ninja/) — Usage recipes
- [Specs: Django Ninja](../../specs/django-ninja/)
