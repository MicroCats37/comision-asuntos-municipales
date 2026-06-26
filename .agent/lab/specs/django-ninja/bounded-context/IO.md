# Bounded Context IO — Interface Contracts Per Layer

## Rule
Each layer within a Bounded Context has clear interfaces (ports) that define how layers communicate.

---

## Domain Layer Interfaces (Ports)

### Repository Port
```python
# domain/repositories.py
from abc import ABC, abstractmethod
from typing import Protocol
from .models import User
from .schemas import UserCreate, UserUpdate

class UserRepository(Protocol):
    """Port for user persistence operations."""
    
    def get_by_id(self, user_id: int) -> User | None: ...
    def get_by_email(self, email: str) -> User | None: ...
    def create(self, data: UserCreate) -> User: ...
    def update(self, user_id: int, data: UserUpdate) -> User: ...
    def delete(self, user_id: int) -> bool: ...
    def list(self, filters: dict) -> list[User]: ...
```

### Selector Port
```python
# domain/selectors.py
from abc import ABC, abstractmethod
from typing import Protocol
from .models import User

class UserSelector(Protocol):
    """Port for user query operations."""
    
    def get_active_users(self) -> list[User]: ...
    def search_by_username(self, query: str) -> list[User]: ...
    def get_users_by_role(self, role: str) -> list[User]: ...
```

### Service Interface
```python
# domain/services.py
from abc import ABC, abstractmethod
from .schemas import AuthCredentials, TokenPair, UserCreate

class AuthService(ABC):
    """Port for authentication operations."""
    
    @abstractmethod
    def authenticate(self, credentials: AuthCredentials) -> TokenPair: ...
    
    @abstractmethod
    def refresh_token(self, refresh_token: str) -> TokenPair: ...
    
    @abstractmethod
    def revoke_token(self, token: str) -> bool: ...
```

---

## Infrastructure Layer Interfaces (Adapters)

### Repository Implementation
```python
# infrastructure/repositories.py
from modulos.identidad.domain.repositories import UserRepository
from modulos.identidad.domain.models import User
from modulos.identidad.domain.schemas import UserCreate, UserUpdate
from django.contrib.auth import get_user_model

UserModel = get_user_model()

class DjangoUserRepository(UserRepository):
    """Adapter: Django ORM implementation of UserRepository."""
    
    def get_by_id(self, user_id: int) -> User | None:
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
    
    def get_by_email(self, email: str) -> User | None:
        try:
            return UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            return None
    
    def create(self, data: UserCreate) -> User:
        user = UserModel.objects.create_user(
            username=data.username,
            email=data.email,
            password=data.password,
        )
        return User.from_django(user)
    
    def update(self, user_id: int, data: UserUpdate) -> User:
        user = UserModel.objects.get(pk=user_id)
        for attr, value in data.dict(exclude_unset=True).items():
            setattr(user, attr, value)
        user.save()
        return User.from_django(user)
    
    def delete(self, user_id: int) -> bool:
        return UserModel.objects.filter(pk=user_id).delete()[0] > 0
    
    def list(self, filters: dict) -> list[User]:
        qs = UserModel.objects.filter(**filters)
        return [User.from_django(u) for u in qs]
```

### Selector Implementation
```python
# infrastructure/selectors.py
from modulos.identidad.domain.selectors import UserSelector
from modulos.identidad.domain.models import User
from django.contrib.auth import get_user_model

UserModel = get_user_model()

class DjangoUserSelector(UserSelector):
    """Adapter: Django ORM implementation of UserSelector."""
    
    def get_active_users(self) -> list[User]:
        users = UserModel.objects.filter(is_active=True)
        return [User.from_django(u) for u in users]
    
    def search_by_username(self, query: str) -> list[User]:
        users = UserModel.objects.filter(username__icontains=query)
        return [User.from_django(u) for u in users]
    
    def get_users_by_role(self, role: str) -> list[User]:
        users = UserModel.objects.filter(groups__name=role)
        return [User.from_django(u) for u in users]
```

---

## Presentation Layer Interfaces

### Controller Schema
```python
# presentation/schemas/auth_schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access: str
    refresh: str
    token_type: str = "bearer"

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    password_confirm: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    
    class Config:
        from_attributes = True
```

### Controller Interface
```python
# presentation/controllers/auth_controller.py
from ninja_extra import api_controller, route
from ninja_jwt.authentication import JWTAuth
from modulos.identidad.domain.services.auth_service import AuthService
from modulos.identidad.domain.services.user_service import UserService
from modulos.identidad.presentation.schemas.auth_schemas import (
    LoginRequest,
    TokenResponse,
    RegisterRequest,
    UserResponse,
)
from injector import inject

@api_controller("/auth", auth=JWTAuth())
class AuthController:
    @inject
    def __init__(self, auth_service: AuthService, user_service: UserService):
        self.auth_service = auth_service
        self.user_service = user_service
    
    @route.post("/login")
    def login(self, data: LoginRequest) -> TokenResponse:
        tokens = self.auth_service.authenticate(data.username, data.password)
        return TokenResponse(
            access=tokens.access,
            refresh=tokens.refresh,
        )
    
    @route.post("/register")
    def register(self, data: RegisterRequest) -> UserResponse:
        user = self.user_service.register(
            username=data.username,
            email=data.email,
            password=data.password,
        )
        return UserResponse.model_validate(user)
    
    @route.get("/me")
    def me(self, request) -> UserResponse:
        user = self.user_service.get_profile(request.user.id)
        return UserResponse.model_validate(user)
```

---

## Cross-Layer Flow

```
HTTP Request
    │
    ▼
presentation/controllers/auth_controller.py
    │  (receives request, validates schema)
    │  (calls domain service)
    ▼
domain/services/auth_service.py
    │  (business logic)
    │  (calls domain repository port)
    ▼
domain/repositories.py (interface only)
    │
    ▼
infrastructure/repositories.py
    │  (implements port using Django ORM)
    ▼
Database
```

Dependencies flow inward: `presentation` → `domain` ← `infrastructure`
