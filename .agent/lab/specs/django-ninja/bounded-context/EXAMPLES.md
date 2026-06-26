# Bounded Context Example — `modulos/identidad/`

## Overview
The `identidad` bounded context handles identity and authentication, including user management, authentication (login/logout), and registration.

## Folder Structure

```
modulos/identidad/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── models.py              # User domain model
│   ├── schemas.py             # Domain schemas
│   ├── services.py            # Service interfaces (ABC)
│   ├── selectors.py           # Selector interfaces (ports)
│   ├── repositories.py        # Repository interfaces (ports)
│   └── exceptions.py          # Domain exceptions
│
├── infrastructure/
│   ├── __init__.py
│   ├── apps.py                # AppConfig for Django
│   ├── models.py               # Django ORM models
│   ├── repositories.py         # Repository implementations
│   ├── selectors.py           # Selector implementations
│   ├── admin/
│   │   ├── __init__.py
│   │   ├── user_admin.py
│   │   └── perfil_admin.py
│   └── services.py             # External integrations
│
└── presentation/
    ├── __init__.py
    ├── controllers/
    │   ├── __init__.py
    │   ├── auth_controller.py
    │   ├── user_controller.py
    │   └── registro_controller.py
    ├── schemas/
    │   ├── __init__.py
    │   ├── auth_schemas.py
    │   └── user_schemas.py
    ├── routers.py
    ├── dependencies.py
    └── urls.py
```

---

## Domain Layer

### `domain/__init__.py`
```python
from .models import User
from .services import AuthService, UserService, RegistroService
from .repositories import UserRepository
from .selectors import UserSelector
from .exceptions import (
    AuthenticationError,
    UserNotFoundError,
    EmailAlreadyExistsError,
)

__all__ = [
    'User',
    'AuthService',
    'UserService',
    'RegistroService',
    'UserRepository',
    'UserSelector',
    'AuthenticationError',
    'UserNotFoundError',
    'EmailAlreadyExistsError',
]
```

### `domain/models.py`
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class User:
    id: int
    username: str
    email: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    @classmethod
    def from_django(cls, django_user) -> 'User':
        return cls(
            id=django_user.pk,
            username=django_user.username,
            email=django_user.email,
            is_active=django_user.is_active,
            is_verified=getattr(django_user, 'is_verified', False),
            created_at=django_user.date_joined,
            last_login=django_user.last_login,
        )
```

### `domain/schemas.py`
```python
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    password_confirm: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class AuthCredentials(BaseModel):
    username: str
    password: str

class TokenPair(BaseModel):
    access: str
    refresh: str
    token_type: str = "bearer"
    expires_in: int

class RegistroData(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
```

### `domain/exceptions.py`
```python
class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass

class UserNotFoundError(Exception):
    """Raised when a user is not found."""
    pass

class EmailAlreadyExistsError(Exception):
    """Raised when email is already registered."""
    pass

class InvalidTokenError(Exception):
    """Raised when a token is invalid or expired."""
    pass
```

### `domain/services.py`
```python
from abc import ABC, abstractmethod
from .models import User
from .schemas import AuthCredentials, TokenPair, RegistroData, UserUpdate

class AuthService(ABC):
    @abstractmethod
    def authenticate(self, credentials: AuthCredentials) -> TokenPair: ...
    
    @abstractmethod
    def refresh_token(self, refresh_token: str) -> TokenPair: ...
    
    @abstractmethod
    def logout(self, user_id: int) -> bool: ...

class UserService(ABC):
    @abstractmethod
    def get_profile(self, user_id: int) -> User: ...
    
    @abstractmethod
    def update_profile(self, user_id: int, data: UserUpdate) -> User: ...

class RegistroService(ABC):
    @abstractmethod
    def register(self, data: RegistroData) -> User: ...
    
    @abstractmethod
    def confirm_email(self, token: str) -> bool: ...
```

### `domain/repositories.py`
```python
from abc import ABC, abstractmethod
from .models import User
from .schemas import UserCreate, UserUpdate

class UserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None: ...
    
    @abstractmethod
    def get_by_email(self, email: str) -> User | None: ...
    
    @abstractmethod
    def create(self, data: UserCreate) -> User: ...
    
    @abstractmethod
    def update(self, user_id: int, data: UserUpdate) -> User: ...
```

### `domain/selectors.py`
```python
from abc import ABC, abstractmethod
from .models import User

class UserSelector(ABC):
    @abstractmethod
    def get_active_users(self) -> list[User]: ...
    
    @abstractmethod
    def search_by_username(self, query: str) -> list[User]: ...
```

---

## Infrastructure Layer

### `infrastructure/__init__.py`
```python
from .models import User, Perfil, Session
from .repositories import DjangoUserRepository
from .selectors import DjangoUserSelector

__all__ = ['User', 'Perfil', 'Session', 'DjangoUserRepository', 'DjangoUserSelector']
```

### `infrastructure/apps.py`
```python
from django.apps import AppConfig

class IdentidadConfig(AppConfig):
    name = 'modulos.identidad.infrastructure'
    label = 'identidad'
    verbose_name = 'Identidad y Autenticación'
```

### `infrastructure/models.py`
```python
from django.contrib.auth.models import User as DjangoUser
from django.db import models
from django.utils import timezone

class Perfil(models.Model):
    user = models.OneToOneField(DjangoUser, on_delete=models.CASCADE, related_name='perfil')
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.TextField(blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    
    class Meta:
        db_table = 'identidad_perfil'

class Session(models.Model):
    user = models.ForeignKey(DjangoUser, on_delete=models.CASCADE, related_name='sessions')
    token = models.CharField(max_length=500, unique=True)
    device_info = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'identidad_session'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'is_active']),
        ]
```

### `infrastructure/repositories.py`
```python
from modulos.identidad.domain.repositories import UserRepository
from modulos.identidad.domain.models import User
from modulos.identidad.domain.schemas import UserCreate, UserUpdate
from modulos.identidad.domain.exceptions import UserNotFoundError
from django.contrib.auth import get_user_model
from django.db import IntegrityError

UserModel = get_user_model()

class DjangoUserRepository(UserRepository):
    def get_by_id(self, user_id: int) -> User | None:
        try:
            django_user = UserModel.objects.get(pk=user_id)
            return User.from_django(django_user)
        except UserModel.DoesNotExist:
            return None
    
    def get_by_email(self, email: str) -> User | None:
        try:
            django_user = UserModel.objects.get(email=email)
            return User.from_django(django_user)
        except UserModel.DoesNotExist:
            return None
    
    def create(self, data: UserCreate) -> User:
        django_user = UserModel.objects.create_user(
            username=data.username,
            email=data.email,
            password=data.password,
        )
        return User.from_django(django_user)
    
    def update(self, user_id: int, data: UserUpdate) -> User:
        django_user = UserModel.objects.get(pk=user_id)
        update_data = data.model_dump(exclude_unset=True)
        for attr, value in update_data.items():
            setattr(django_user, attr, value)
        django_user.save()
        return User.from_django(django_user)
```

### `infrastructure/admin/__init__.py`
```python
from .user_admin import UserAdmin
from .perfil_admin import PerfilAdmin

__all__ = ['UserAdmin', 'PerfilAdmin']
```

### `infrastructure/admin/user_admin.py`
```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth import get_user_model
from modulos.identidad.infrastructure.models import Perfil

UserModel = get_user_model()

@admin.register(UserModel)
class UserAdmin(DjangoUserAdmin):
    list_display = ('username', 'email', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = DjangoUserAdmin.fieldsets + (
        ('Verificación', {'fields': ('is_verified',)}),
    )
    
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ('Información adicional', {
            'fields': ('email',)
        }),
    )
```

### `infrastructure/admin/perfil_admin.py`
```python
from django.contrib import admin
from modulos.identidad.infrastructure.models import Perfil

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'telefono', 'direccion', 'fecha_nacimiento')
    search_fields = ('user__username', 'user__email', 'telefono')
    list_filter = ('fecha_nacimiento',)
    autocomplete_fields = ('user',)
```

---

## Presentation Layer

### `presentation/schemas/auth_schemas.py`
```python
from pydantic import BaseModel, Field
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access: str
    refresh: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh: str

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., format='email')
    password: str = Field(..., min_length=8)
    password_confirm: str
```

### `presentation/schemas/user_schemas.py`
```python
from pydantic import BaseModel, EmailStr
from typing import Optional

class UserProfileResponse(BaseModel):
    id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    
    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
```

### `presentation/controllers/auth_controller.py`
```python
from ninja_extra import api_controller, route
from ninja_jwt.authentication import JWTAuth
from injector import inject
from modulos.identidad.domain.services.auth_service import AuthService
from modulos.identidad.presentation.schemas.auth_schemas import (
    LoginRequest,
    TokenResponse,
    RefreshRequest,
)

@api_controller("/auth")
class AuthController:
    @inject
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service
    
    @route.post("/login")
    def login(self, data: LoginRequest) -> TokenResponse:
        from modulos.identidad.domain.schemas import AuthCredentials
        credentials = AuthCredentials(username=data.username, password=data.password)
        tokens = self.auth_service.authenticate(credentials)
        return TokenResponse(
            access=tokens.access,
            refresh=tokens.refresh,
        )
    
    @route.post("/refresh")
    def refresh(self, data: RefreshRequest) -> TokenResponse:
        tokens = self.auth_service.refresh_token(data.refresh)
        return TokenResponse(
            access=tokens.access,
            refresh=tokens.refresh,
        )
```

### `presentation/controllers/user_controller.py`
```python
from ninja_extra import api_controller, route
from ninja_jwt.authentication import JWTAuth
from injector import inject
from modulos.identidad.domain.services.user_service import UserService
from modulos.identidad.presentation.schemas.user_schemas import (
    UserProfileResponse,
    UserProfileUpdate,
)

@api_controller("/users", auth=JWTAuth())
class UserController:
    @inject
    def __init__(self, user_service: UserService):
        self.user_service = user_service
    
    @route.get("/me")
    def get_me(self, request) -> UserProfileResponse:
        user = self.user_service.get_profile(request.user.id)
        return UserProfileResponse.model_validate(user)
    
    @route.patch("/me")
    def update_me(self, request, data: UserProfileUpdate) -> UserProfileResponse:
        user = self.user_service.update_profile(request.user.id, data)
        return UserProfileResponse.model_validate(user)
```

### `presentation/controllers/registro_controller.py`
```python
from ninja_extra import api_controller, route
from injector import inject
from modulos.identidad.domain.services.registro_service import RegistroService
from modulos.identidad.presentation.schemas.auth_schemas import RegisterRequest
from modulos.identidad.presentation.schemas.user_schemas import UserProfileResponse

@api_controller("/registro")
class RegistroController:
    @inject
    def __init__(self, registro_service: RegistroService):
        self.registro_service = registro_service
    
    @route.post("/register")
    def register(self, data: RegisterRequest) -> UserProfileResponse:
        from modulos.identidad.domain.schemas import RegistroData
        registro_data = RegistroData(
            username=data.username,
            email=data.email,
            password=data.password,
        )
        user = self.registro_service.register(registro_data)
        return UserProfileResponse.model_validate(user)
```
