# Django Ninja: JWT Authentication

> **PRIMARY STANDARD** — Use `django-ninja-jwt` for all authentication. Use `NinjaJWTDefaultController` for token endpoints.

## Overview

`django-ninja-jwt` provides JWT (JSON Web Token) authentication for Django Ninja. It includes token generation, refresh, and validation via the `JWTAuth` decorator.

## Installation

```bash
pip install django-ninja-jwt
```

## Setup

```python
from ninja_extra import NinjaExtraAPI
from ninja_jwt.controller import NinjaJWTDefaultController

api = NinjaExtraAPI()
api.register_controllers(NinjaJWTDefaultController)
```

This registers four endpoints:
- `POST /api/token/` — Obtain token pair (access + refresh)
- `POST /api/token/refresh/` — Refresh access token
- `POST /api/token/verify/` — Verify a token
- `GET /api/token/blacklist/` — Blacklist a refresh token (requires app authentication)

## Token Generation for Users

```python
from ninja_jwt.tokens import RefreshToken

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }
```

## Using JWT Auth on Routes

### Using the `auth` Parameter

```python
from ninja_extra import api_controller, route
from ninja_jwt.authentication import JWTAuth

@api_controller("/profile", tags=['Profile'])
class ProfileController:
    
    @route.get("/me", auth=JWTAuth())
    def get_my_profile(self, request):
        """Requires valid JWT. User available at request.user."""
        return {
            "user": request.user.username,
            "email": request.user.email,
        }
```

### Combining JWT Auth with Permissions

```python
from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated
from ninja_jwt.authentication import JWTAuth

@api_controller("/articles", tags=['Articles'])
class ArticleController:
    
    @route.get("/", auth=JWTAuth())
    def list_articles(self, request):
        """Auth required."""
        return Article.objects.filter(author=request.user)
    
    @route.post("/", auth=JWTAuth(), permissions=[IsAuthenticated])
    def create_article(self, request, data: ArticleCreateSchema):
        """Auth + permission check."""
        return Article.objects.create(**data.dict(), author=request.user)
```

## Customizing JWT Settings

In `settings.py`:

```python
NINJA_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': settings.SECRET_KEY,
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

## Manual Token Validation

```python
from ninja_jwt.authentication import JWTAuth
from rest_framework.exceptions import AuthenticationFailed

def validate_token(token: str) -> User:
    auth = JWTAuth()
    try:
        user = auth.authenticate(token)
        return user
    except AuthenticationFailed:
        return None
```

## Async JWT Auth

```python
from ninja_extra import api_controller, route
from ninja_jwt.authentication import JWTAuth

@api_controller("/async-profile", tags=['Profile'])
class AsyncProfileController:
    
    @route.get("/me", auth=JWTAuth())
    async def get_my_profile(self, request):
        """Async endpoint with JWT auth."""
        return {
            "user": request.user.username,
            "email": request.user.email,
        }
```

## Custom Token Controllers

Extend `NinjaJWTDefaultController` for custom behavior:

```python
from ninja_jwt.controller import NinjaJWTDefaultController
from ninja_extra import api_controller

@api_controller("/auth", tags=['Authentication'])
class CustomAuthController(NinjaJWTDefaultController):
    """Adds custom endpoints alongside default JWT ones."""
    
    @route.post("/register/")
    def register(self, data: UserCreateSchema):
        user = User.objects.create_user(**data.dict())
        return get_tokens_for_user(user)
```

## See Also

- [Pattern: JWT Auth Usage](../../patterns/django-ninja/jwt-auth-usage.md)
- [Knowledge: Class-Based Controllers](./class-based-controllers.md)
- [Knowledge: Permissions](./permissions.md)
