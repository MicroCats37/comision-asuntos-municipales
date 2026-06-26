# Django Ninja: Selectors (Infrastructure Layer)

## Overview
Selectors are query classes that encapsulate complex read-only database operations. In our Hexagonal architecture, the concrete implementations live in the `infrastructure/` layer, while their interfaces (ports) live in the `domain/` layer.

## Key Concepts
- **Infrastructure concern**: Selectors interact directly with the Django ORM.
- **Implement Interfaces**: Concrete selectors inherit from domain `Protocol`s.
- **Read-only**: Never mutate data.
- **Injected**: Injected into domain services or controllers via `@inject`.

## Selector Anatomy
```python
# domain/interfaces.py
from typing import Protocol

class IUserSelector(Protocol):
    def get_active_users(self) -> list[dict]: ...

# infrastructure/selectors.py
from ..domain.interfaces import IUserSelector
from .models import UserORM

class DjangoUserSelector(IUserSelector):
    def get_active_users(self) -> list[dict]:
        # ORM specific logic
        qs = UserORM.objects.filter(status="active").values("id", "email")
        return list(qs)
```

## See Also
- [Knowledge: Hexagonal Architecture](./hexagonal-architecture.md)
- [Spec: Project Structure](../../specs/django-ninja/project-structure/SPEC.md)