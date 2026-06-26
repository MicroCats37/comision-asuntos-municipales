# Django Ninja: Permissions

> **PRIMARY STANDARD** — Use permission arrays on controllers and routes for authorization.

## Overview

`django-ninja-extra` provides a comprehensive permission system built on Django's auth permissions. Permissions can be applied at the controller level (inherited by all routes) or overridden at the route level.

## Built-in Permissions

| Permission | Description |
|------------|-------------|
| `AllowAny` | No restrictions — public endpoint |
| `IsAuthenticated` | User must be authenticated |
| `IsAdminUser` | User must be `is_staff=True` |
| `IsAuthenticatedOrReadOnly` | Auth for write, public for read |
| `DjangoModelPermissions` | Uses Django's model-level permissions |
| `DjangoObjectPermissions` | Per-object auth (requires `queryset`) |

## Permission Application

### Controller-Level (Applies to All Routes)

```python
from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated, IsAdminUser

@api_controller("/admin", tags=['Admin'], permissions=[IsAdminUser])
class AdminController:
    
    @route.get("/stats")
    def get_stats(self):
        return {"total_users": User.objects.count()}
    
    @route.post("/flush-cache")
    def flush_cache(self):
        cache.clear()
        return {"status": "ok"}
```

### Route-Level Override

```python
from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated, AllowAny

@api_controller("/articles", tags=['Articles'])
class ArticleController:
    
    @route.get("/", permissions=[AllowAny])
    def list_articles(self):
        """Public endpoint — anyone can list articles."""
        return Article.objects.all()
    
    @route.post("/", permissions=[IsAuthenticated])
    def create_article(self, data: ArticleCreateSchema, request):
        """Protected endpoint — auth required."""
        return Article.objects.create(**data.dict(), author=request.user)
```

### Permission Stacking

Permissions are additive — a user must satisfy ALL permissions in the array:

```python
@api_controller("/premium", permissions=[IsAuthenticated, IsAdminUser])
class PremiumController:
    """User must be BOTH authenticated AND admin."""
```

## Custom Permissions

### Function-Based Permission

```python
from ninja_extra.permissions import BasePermission

def IsAuthorOrAdmin(BasePermission):
    def has_permission(self, request, view) -> bool:
        return request.user and (
            request.user.is_staff or 
            getattr(view, 'obj', None) and view.obj.author == request.user
        )
    
    def has_object_permission(self, request, view, obj) -> bool:
        return request.user.is_staff or obj.author == request.user
```

### Class-Based Permission with Dependencies

```python
from ninja_extra.permissions import BasePermission
from injector import inject

class HasSubscription(BasePermission):
    @inject
    def __init__(self, subscription_service: SubscriptionService):
        self.subscription_service = subscription_service
    
    def has_permission(self, request, view) -> bool:
        if not request.user:
            return False
        return self.subscription_service.has_active(request.user)
```

### Async Permission

```python
from ninja_extra.permissions import AsyncBasePermission

class AsyncIsVerifiedUser(AsyncBasePermission):
    @inject
    def __init__(self, verification_service: VerificationService):
        self.verification_service = verification_service
    
    async def async_has_permission(self, request, view) -> bool:
        return await self.verification_service.is_verified(request.user)
```

## Using Permissions in Routes

```python
from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated

@api_controller("/documents", tags=['Documents'])
class DocumentController:
    
    @route.get("/{doc_id}")
    def get_document(self, doc_id: int):
        """Any user can view documents."""
        return Document.objects.get(id=doc_id)
    
    @route.delete("/{doc_id}", permissions=[IsAuthenticated])
    def delete_document(self, doc_id: int, request):
        """Only authenticated users can delete."""
        doc = Document.objects.get(id=doc_id)
        doc.delete()
        return None
```

## Permission in Class Controllers with `@inject`

```python
from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated, BasePermission
from injector import inject

class IsOwner(BasePermission):
    @inject
    def __init__(self, ownership_service: OwnershipService):
        self.ownership_service = ownership_service
    
    def has_object_permission(self, request, view, obj) -> bool:
        return self.ownership_service.is_owner(request.user, obj)

@api_controller("/items", tags=['Items'])
class ItemController:
    
    @inject
    def __init__(self, item_service: ItemService, ownership_service: OwnershipService):
        self.item_service = item_service
        self.ownership_service = ownership_service
    
    @route.get("/{item_id}")
    def get_item(self, item_id: int):
        return self.item_service.get(item_id)
    
    @route.put("/{item_id}", permissions=[IsOwner])
    def update_item(self, item_id: int, data: ItemUpdateSchema, request):
        item = self.item_service.get(item_id)
        return self.item_service.update(item, data)
```

## See Also

- [Knowledge: Class-Based Controllers](./class-based-controllers.md)
- [Knowledge: Constructor DI](./constructor-di.md)
- [Knowledge: JWT Auth](./jwt-auth.md)
