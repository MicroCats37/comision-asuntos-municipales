# Pattern: Class Controller Usage

> **PRIMARY STANDARD** — Use `@api_controller` from `django-ninja-extra` for all new endpoints.

## Use Case

Building a User management API with list, retrieve, create, update, and delete operations using class-based controllers.

## Example: UserController

```python
# myapp/controllers/user_controller.py
from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated, AllowAny
from ninja import Schema
from typing import List

class UserResponseSchema(Schema):
    id: int
    username: str
    email: str
    is_active: bool

class UserCreateSchema(Schema):
    username: str
    email: str
    password: str

class UserUpdateSchema(Schema):
    username: str | None = None
    email: str | None = None
    is_active: bool | None = None

@api_controller("/users", tags=['Users'], permissions=[AllowAny])
class UserController:
    
    @route.get("/", response=List[UserResponseSchema])
    def list_users(self, limit: int = 10, offset: int = 0):
        """List all users with pagination."""
        users = User.objects.all()[offset:offset + limit]
        return users
    
    @route.get("/{user_id}", response=UserResponseSchema)
    def get_user(self, user_id: int):
        """Get a single user by ID."""
        return User.objects.get(id=user_id)
    
    @route.post("/", response=UserResponseSchema, permissions=[AllowAny])
    def create_user(self, data: UserCreateSchema):
        """Create a new user."""
        user = User.objects.create_user(
            username=data.username,
            email=data.email,
            password=data.password
        )
        return user
    
    @route.put("/{user_id}", response=UserResponseSchema)
    def update_user(self, user_id: int, data: UserUpdateSchema):
        """Full update of a user."""
        user = User.objects.get(id=user_id)
        for field, value in data.dict(exclude_unset=True).items():
            setattr(user, field, value)
        user.save()
        return user
    
    @route.patch("/{user_id}", response=UserResponseSchema)
    def patch_user(self, user_id: int, data: UserUpdateSchema):
        """Partial update of a user."""
        return self.update_user(user_id, data)
    
    @route.delete("/{user_id}")
    def delete_user(self, user_id: int):
        """Delete a user."""
        user = User.objects.get(id=user_id)
        user.delete()
        return {"deleted": True}
```

## Use Case

Adding constructor dependency injection to a controller with multiple services.

## Example: ArticleController with CDI

```python
# myapp/controllers/article_controller.py
from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated
from ninja_extra.schemas import NinjaAPIRequest
from ninja import Schema
from injector import inject
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
    
    @inject
    def __init__(
        self,
        article_service: "ArticleService",
        notification_service: "NotificationService"
    ):
        self.article_service = article_service
        self.notification_service = notification_service
    
    @route.get("/", response=List[ArticleResponseSchema])
    def list_articles(self, published_only: bool = True):
        if published_only:
            return self.article_service.get_published()
        return self.article_service.get_all()
    
    @route.get("/{article_id}", response=ArticleResponseSchema)
    def get_article(self, article_id: int):
        return self.article_service.get_by_id(article_id)
    
    @route.post("/", response=ArticleResponseSchema, permissions=[IsAuthenticated])
    def create_article(self, data: ArticleCreateSchema, request: NinjaAPIRequest):
        article = self.article_service.create(
            title=data.title,
            content=data.content,
            published=data.published,
            author=request.user
        )
        self.notification_service.notify_new_article(article)
        return article
    
    @route.delete("/{article_id}", permissions=[IsAuthenticated])
    def delete_article(self, article_id: int, request: NinjaAPIRequest):
        article = self.article_service.get_by_id(article_id)
        if article.author != request.user and not request.user.is_staff:
            raise PermissionError("Not your article")
        self.article_service.delete(article)
        return {"deleted": True}
```

## Use Case

Controller with permission overrides and nested controllers.

## Example: AdminController with Nested Resources

```python
# myapp/controllers/admin_controller.py
from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAdminUser
from ninja import Schema
from typing import List

@api_controller("/admin", tags=['Admin'], permissions=[IsAdminUser])
class AdminController:
    """Base admin controller — all routes require admin."""
    
    @route.get("/dashboard")
    def dashboard(self, request):
        return {
            "total_users": User.objects.count(),
            "total_articles": Article.objects.count(),
        }

@api_controller("/admin/users", tags=['Admin'], permissions=[IsAdminUser])
class AdminUserController(AdminController):
    """Admin user management — inherits admin permission."""
    
    @route.get("/", response=List[UserSchema])
    def list_all_users(self):
        return User.objects.all()
    
    @route.post("/{user_id}/activate")
    def activate_user(self, user_id: int):
        user = User.objects.get(id=user_id)
        user.is_active = True
        user.save()
        return {"status": "activated"}
    
    @route.post("/{user_id}/deactivate")
    def deactivate_user(self, user_id: int):
        user = User.objects.get(id=user_id)
        user.is_active = False
        user.save()
        return {"status": "deactivated"}
```

## See Also

- [Knowledge: Class-Based Controllers](../../knowledge/django-ninja/class-based-controllers.md)
- [Pattern: Constructor DI Usage](../../patterns/django-ninja/constructor-di-usage.md)
- [Pattern: JWT Auth Usage](../../patterns/django-ninja/jwt-auth-usage.md)
