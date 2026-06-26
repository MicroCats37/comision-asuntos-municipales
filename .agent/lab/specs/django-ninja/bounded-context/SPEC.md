# Bounded Context Spec — 1 Django App = 1 Bounded Context

## Rule
Each Django app represents a single **Bounded Context** — a cohesive domain of business capability. This is NOT the same as "1 app per model" (over-fragmentation) nor "1 app for everything" (monolith).

## Context
A Bounded Context defines a clear boundary where a particular domain model exists. Within this boundary, all business concepts are related and consistent. Between boundaries, models may differ (e.g., "User" in identity context vs "Customer" in billing context).

---

## REQUIRED — Bounded Context Scope

### 1 App = 1 Bounded Context
```
modulos/
├── identidad/          # Identity & Authentication domain
│   ├── domain/
│   ├── infrastructure/
│   └── presentation/
│
└── facturacion/        # Billing domain (separate bounded context)
    ├── domain/
    ├── infrastructure/
    └── presentation/
```

### Internal Structure (per app)
Each bounded context app contains three subdirectories:

```
myapp/
├── domain/                  # Pure business logic — NO framework imports
│   ├── __init__.py
│   ├── models.py            # Domain entities (Pydantic or Django ORM)
│   ├── schemas.py           # Domain schemas
│   ├── services.py          # Business logic services
│   ├── selectors.py         # Query interfaces (ports)
│   ├── repositories.py      # Persistence interfaces (ports)
│   └── exceptions.py        # Domain exceptions
│
├── infrastructure/          # Framework adapters — implements domain interfaces
│   ├── __init__.py
│   ├── models.py            # Django ORM models (for migrations)
│   ├── repositories.py      # Repository implementations
│   ├── selectors.py         # Selector implementations
│   ├── admin/               # Django admin (one file per model)
│   │   ├── __init__.py
│   │   ├── user_admin.py
│   │   └── perfil_admin.py
│   └── services.py         # External integrations (email, cache)
│
└── presentation/            # HTTP adapters
    ├── __init__.py
    ├── controllers/          # One controller file per concept
    │   ├── __init__.py
    │   ├── auth_controller.py
    │   ├── user_controller.py
    │   └── registro_controller.py
    ├── schemas/              # Pydantic schemas for HTTP layer
    │   ├── __init__.py
    │   ├── auth_schemas.py
    │   └── user_schemas.py
    ├── routers.py
    ├── dependencies.py
    └── urls.py
```

---

## REQUIRED — File → Folder Promotion

When a file grows too large, convert it to a folder with `__init__.py`:

| Original | Promoted To |
|----------|-------------|
| `admin.py` | `admin/__init__.py` + `admin/user_admin.py`, `admin/perfil_admin.py` |
| `models.py` (large) | `models/` folder with separate model files |
| `services.py` (large) | Split into multiple service files per concept |

### Admin Promotion Example
```python
# admin/__init__.py
from .user_admin import UserAdmin
from .perfil_admin import PerfilAdmin

# admin/user_admin.py
from django.contrib import admin
from modulos.identidad.infrastructure.models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_active')
    search_fields = ('username', 'email')
```

---

## REQUIRED — Models Location (`infrastructure/models.py`)

Django requires `models.py` to be importable from the app root for migration discovery. To keep models in `infrastructure/`:

### Option A: Re-export in `__init__.py`
```python
# modulos/identidad/__init__.py
from .infrastructure.models import (
    User,
    Perfil,
    Session,
)

__all__ = ['User', 'Perfil', 'Session']
```

### Option B: Configure `AppConfig`
```python
# modulos/identidad/infrastructure/apps.py
from django.apps import AppConfig

class IdentidadConfig(AppConfig):
    name = 'modulos.identidad.infrastructure'
    label = 'identidad'
```

Then in `settings.INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    'modulos.identidad.infrastructure.apps.IdentidadConfig',
    # NOT 'modulos.identidad'
]
```

---

## REQUIRED — Multiple Services Per Context

When a bounded context contains multiple related concepts, separate them into distinct service/controller/schema files:

```python
# identidad/domain/services/auth_service.py
class AuthService:
    def authenticate(self, username: str, password: str) -> TokenPair: ...

# identidad/domain/services/user_service.py
class UserService:
    def get_profile(self, user_id: int) -> User: ...
    def update_profile(self, user_id: int, data: ProfileUpdate) -> User: ...

# identidad/domain/services/registro_service.py
class RegistroService:
    def register(self, data: RegistroData) -> User: ...
    def confirm_email(self, token: str) -> bool: ...
```

---

## FORBIDDEN — Anti-Patterns

### ❌ 1 App Per Model (Over-Fragmentation)
```
apps/
├── user/
├── perfil/
├── session/
└── permiso/
```
**Why**: Fragments the domain, breaks transactional boundaries, creates import chaos.

### ❌ 1 Single App For Everything (Monolith)
```
mi_proyecto/
├── models.py      # 200+ models
├── views.py        # 500+ views
└── admin.py        # 300+ lines
```
**Why**: Loses domain clarity, creates circular dependencies, impossible to test.

### ❌ Business Logic in Controllers or Models
```python
# ❌ WRONG — business logic in controller
@api_controller("/users")
class UserController:
    def create_user(self, data):
        if User.objects.filter(email=data.email).exists():
            raise ConflictError("Email taken")
        user = User.objects.create(**data.dict())
        send_welcome_email(user)
        return user

# ✅ CORRECT — business logic in service
@api_controller("/users")
class UserController:
    def __init__(self, user_service: UserService):
        self.user_service = user_service

    def create_user(self, data):
        return self.user_service.register_user(data)
```

---

## Decision Log
- v1.0: Introduced bounded context pattern to replace both over-fragmented and monolithic app structures
- v1.0: Specified domain/infrastructure/presentation layers within each bounded context
- v1.0: Added file→folder promotion rules for growing files
- v1.0: Established models location in infrastructure/ with re-export pattern
