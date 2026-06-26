# Django Ninja: Services (Domain Layer)

## Overview
Service classes encapsulate pure business logic in our DDD-lite Hexagonal architecture. They live in the `domain/` layer, have NO dependencies on the Django ORM or HTTP framework, and are injected into controllers using `django-ninja-extra`'s `@inject`.

## Key Concepts
- **Pure Python classes**: No ORM models, no HTTP logic.
- **Port Interfaces**: Services interact with the database via Interfaces (`Protocol`/`ABC`), not concrete ORM models.
- **Constructor Injection**: Services declare their dependencies in the `__init__` via `@inject`.
- **Domain location**: Always located in `myapp/domain/services.py`.

## Service Anatomy
```python
from ninja_extra.di import inject
from .interfaces import IUserRepository

class UserService:
    @inject
    def __init__(self, repo: IUserRepository):
        self.repo = repo

    def process_registration(self, user_data: dict) -> dict:
        # Pure business logic
        user_data["status"] = "active"
        return self.repo.save(user_data)
```

## See Also
- [Knowledge: Hexagonal Architecture](./hexagonal-architecture.md)
- [Spec: Project Structure](../../specs/django-ninja/project-structure/SPEC.md)