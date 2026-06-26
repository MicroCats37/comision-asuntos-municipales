# Django Ninja: Constructor Dependency Injection

> **PRIMARY STANDARD** — Use `@inject` from `injector` with constructor injection for all service dependencies.

## Overview

Constructor dependency injection (CDI) in `django-ninja-extra` uses the `injector` library to inject services into controllers at instantiation time. This differs from Ninja's `Depends()` which resolves dependencies per-request.

## Key Concepts

- **`@inject` decorator**: Marks `__init__` parameters for injection via the `injector` library.
- **Constructor injection**: Services are constructor parameters, stored as `self.service`.
- **Request-scoped**: NinjaExtraAPI's container provides request context to injected services.
- **Type annotations required**: All injected params must have type annotations.

## Constructor DI vs `Depends()`

| Aspect | `Depends()` (Per-Request) | Constructor Injection (`@inject`) |
|--------|---------------------------|----------------------------------|
| Resolution | Each endpoint call | Controller instantiation |
| State | Always fresh | One instance per request |
| Verbosity | More `Depends()` calls | Cleaner, grouped in `__init__` |
| Testing | Override per-call | Override at controller level |
| Best for | Simple, stateless endpoints | Complex controllers with many deps |

## Injector Setup

Services must be bound to the NinjaExtraAPI container:

```python
from injector import Module, provider
from ninja_extra import NinjaExtraAPI

class ServiceModule(Module):
    @provider
    def provide_user_service(self) -> UserService:
        return UserService()
    
    @provider
    def provide_email_service(self) -> EmailService:
        return EmailService()

api = NinjaExtraAPI()
api.container = ServiceModule
```

## Controller with Constructor Injection

```python
from ninja_extra import api_controller, route
from injector import inject

@api_controller("/users", tags=['Users'])
class UserController:
    
    @inject
    def __init__(self, user_service: UserService):
        self.user_service = user_service
    
    @route.get("/{user_id}")
    def get_user(self, user_id: int):
        return self.user_service.get_by_id(user_id)
    
    @route.post("/")
    def create_user(self, data: UserCreateSchema):
        return self.user_service.create(data)
```

## Multiple Services

```python
from ninja_extra import api_controller, route
from injector import inject

@api_controller("/articles", tags=['Articles'])
class ArticleController:
    
    @inject
    def __init__(
        self, 
        article_service: ArticleService,
        permission_service: PermissionService,
        notification_service: NotificationService
    ):
        self.article_service = article_service
        self.permission_service = permission_service
        self.notification_service = notification_service
    
    @route.post("/", permissions=[IsAuthenticated])
    def create_article(self, data: ArticleCreateSchema, request):
        article = self.article_service.create(data, author=request.user)
        self.notification_service.notify_new_article(article)
        return article
```

## Interface-Based Injection

Use abstractions (protocols/interfaces) for testability:

```python
from typing import Protocol

class UserServiceProtocol(Protocol):
    def get_by_id(self, user_id: int) -> User: ...
    def create(self, data: UserCreateSchema) -> User: ...

class UserServiceImpl:
    def __init__(self, db: "Database"):
        self.db = db
    
    def get_by_id(self, user_id: int) -> User:
        return self.db.query(User).get(user_id)

class ServiceModule(Module):
    @provider
    def provide_user_service(self, impl: UserServiceImpl) -> UserServiceProtocol:
        return impl
```

## Request-Scoped Context

Inject `NinjaAPIRequest` to access the current request:

```python
from ninja_extra import api_controller, route
from ninja_extra.schemas import NinjaAPIRequest
from injector import inject

@api_controller("/profile", tags=['Profile'])
class ProfileController:
    
    @inject
    def __init__(self, profile_service: ProfileService, request: NinjaAPIRequest):
        self.profile_service = profile_service
        self.request = request  # Current HTTP request
    
    @route.get("/me")
    def get_my_profile(self):
        return self.profile_service.get_for_user(self.request.user)
```

## Testing with CDI

Override dependencies at the controller level:

```python
from unittest.mock import Mock

# Create controller with mocked service
mock_service = Mock(spec=UserService)
mock_service.get_by_id.return_value = User(id=1, name="Test")

controller = UserController(user_service=mock_service)
response = controller.get_user(user_id=1)

mock_service.get_by_id.assert_called_once_with(1)
```

## See Also

- [Pattern: Constructor DI Usage](../../patterns/django-ninja/constructor-di-usage.md)
- [Knowledge: Class-Based Controllers](./class-based-controllers.md)
- [Knowledge: Permissions](./permissions.md)
