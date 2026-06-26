# Pattern: JWT Auth Usage

> **PRIMARY STANDARD** — Use `django-ninja-jwt` for all authentication. Register `NinjaJWTDefaultController` for token endpoints.

## Use Case

Setting up JWT authentication with `django-ninja-jwt` and using `JWTAuth()` on protected routes.

## Example: Complete JWT Setup

### 1. Install and Configure

```bash
pip install django-ninja-jwt
```

```python
# settings.py
from datetime import timedelta

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

### 2. API Registration

```python
# myapp/api.py
from ninja_extra import NinjaExtraAPI
from ninja_jwt.controller import NinjaJWTDefaultController

api = NinjaExtraAPI()
api.register_controllers(NinjaJWTDefaultController)
```

### 3. Token Generation Helper

```python
# myapp/jwt_utils.py
from ninja_jwt.tokens import RefreshToken, AccessToken

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

def get_access_token_for_user(user):
    access = AccessToken.for_user(user)
    return str(access)
```

## Example: Protected Controller with JWT

```python
# myapp/controllers/profile_controller.py
from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated
from ninja_jwt.authentication import JWTAuth
from ninja import Schema
from typing import List

class ProfileResponseSchema(Schema):
    id: int
    username: str
    email: str
    bio: str | None

class ProfileUpdateSchema(Schema):
    bio: str | None = None

@api_controller("/profile", tags=['Profile'])
class ProfileController:
    
    @route.get("/me", response=ProfileResponseSchema, auth=JWTAuth())
    def get_my_profile(self, request):
        """Get current user's profile. Requires JWT."""
        return request.user.profile
    
    @route.patch("/me", response=ProfileResponseSchema, auth=JWTAuth())
    def update_my_profile(self, request, data: ProfileUpdateSchema):
        """Update current user's profile. Requires JWT."""
        profile = request.user.profile
        if data.bio is not None:
            profile.bio = data.bio
        profile.save()
        return profile
```

## Example: Article Controller with JWT + Permissions

```python
# myapp/controllers/article_controller.py
from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated, AllowAny
from ninja_jwt.authentication import JWTAuth
from ninja import Schema
from typing import List

class ArticleResponseSchema(Schema):
    id: int
    title: str
    content: str
    author_id: int
    published: bool

class ArticleCreateSchema(Schema):
    title: str
    content: str
    published: bool = False

@api_controller("/articles", tags=['Articles'])
class ArticleController:
    
    @route.get("/", response=List[ArticleResponseSchema], permissions=[AllowAny])
    def list_articles(self):
        """Public endpoint - anyone can list published articles."""
        return Article.objects.filter(published=True)
    
    @route.get("/{article_id}", response=ArticleResponseSchema, permissions=[AllowAny])
    def get_article(self, article_id: int):
        """Public endpoint - anyone can read an article."""
        return Article.objects.get(id=article_id)
    
    @route.post("/", response=ArticleResponseSchema, auth=JWTAuth(), permissions=[IsAuthenticated])
    def create_article(self, request, data: ArticleCreateSchema):
        """Protected - requires JWT and authentication."""
        return Article.objects.create(
            **data.dict(),
            author=request.user
        )
    
    @route.put("/{article_id}", response=ArticleResponseSchema, auth=JWTAuth())
    def update_article(self, request, article_id: int, data: ArticleCreateSchema):
        """Protected - only author can update."""
        article = Article.objects.get(id=article_id)
        if article.author != request.user:
            raise PermissionError("Not the author")
        for key, value in data.dict().items():
            setattr(article, key, value)
        article.save()
        return article
    
    @route.delete("/{article_id}", auth=JWTAuth())
    def delete_article(self, request, article_id: int):
        """Protected - only author can delete."""
        article = Article.objects.get(id=article_id)
        if article.author != request.user and not request.user.is_staff:
            raise PermissionError("Not authorized")
        article.delete()
        return {"deleted": True}
```

## Example: Custom Auth Controller with Registration

```python
# myapp/controllers/auth_controller.py
from ninja_extra import api_controller, route
from ninja_jwt.controller import NinjaJWTDefaultController
from ninja_jwt.authentication import JWTAuth
from ninja import Schema

class UserCreateSchema(Schema):
    username: str
    email: str
    password: str

class TokenPairSchema(Schema):
    refresh: str
    access: str

def get_tokens_for_user(user):
    from ninja_jwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)
    return TokenPairSchema(
        refresh=str(refresh),
        access=str(refresh.access_token)
    )

@api_controller("/auth", tags=['Authentication'])
class AuthController(NinjaJWTDefaultController):
    """Extends default JWT controller with registration."""
    
    @route.post("/register/", response=TokenPairSchema)
    def register(self, data: UserCreateSchema):
        user = User.objects.create_user(
            username=data.username,
            email=data.email,
            password=data.password
        )
        return get_tokens_for_user(user)
```

## Example: Testing JWT-Protected Endpoints

```python
# tests/test_article_api.py
from ninja.testing import TestClient
from myapp.api import api
from myapp.factories import UserFactory, ArticleFactory
from ninja_jwt.tokens import RefreshToken

client = TestClient(api)

@pytest.fixture
def auth_headers():
    user = UserFactory()
    refresh = RefreshToken.for_user(user)
    return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}

def test_list_articles_public():
    response = client.get("/articles/")
    assert response.status_code == 200

def test_create_article_requires_auth():
    response = client.post("/articles/", json={
        'title': 'Test',
        'content': 'Content'
    })
    assert response.status_code == 401

def test_create_article_with_jwt(auth_headers):
    response = client.post(
        "/articles/",
        json={'title': 'Test', 'content': 'Content'},
        headers=auth_headers
    )
    assert response.status_code == 201
    assert response.json()['title'] == 'Test'
```

## See Also

- [Knowledge: JWT Auth](../../knowledge/django-ninja/jwt-auth.md)
- [Knowledge: Class-Based Controllers](../../knowledge/django-ninja/class-based-controllers.md)
- [Knowledge: Permissions](../../knowledge/django-ninja/permissions.md)
