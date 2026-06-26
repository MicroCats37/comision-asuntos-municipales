# Pattern: Constructor DI Usage

> **PRIMARY STANDARD** — Use `@inject` from `injector` for service dependencies in controllers.

## Use Case

Injecting services into a controller using constructor injection pattern with `django-ninja-extra`.

## Example: Service Layer Setup

```python
# myapp/services/user_service.py
from typing import Protocol, List

class UserServiceProtocol(Protocol):
    def get_by_id(self, user_id: int) -> "User": ...
    def get_all(self) -> List["User"]: ...
    def create(self, username: str, email: str, password: str) -> "User": ...
    def update(self, user_id: int, **kwargs) -> "User": ...
    def delete(self, user_id: int) -> None: ...

class UserService:
    def __init__(self, db: "Database"):
        self.db = db
    
    def get_by_id(self, user_id: int) -> "User":
        return self.db.query(User).get(user_id)
    
    def get_all(self) -> List["User"]:
        return list(self.db.query(User).all())
    
    def create(self, username: str, email: str, password: str) -> "User":
        return User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
    
    def update(self, user_id: int, **kwargs) -> "User":
        user = self.get_by_id(user_id)
        for key, value in kwargs.items():
            setattr(user, key, value)
        user.save()
        return user
    
    def delete(self, user_id: int) -> None:
        user = self.get_by_id(user_id)
        user.delete()
```

## Example: Injector Module Configuration

```python
# myapp/api/injection.py
from injector import Module, provider
from myapp.services.user_service import UserService, UserServiceProtocol

class ServiceModule(Module):
    @provider
    def provide_user_service(self) -> UserServiceProtocol:
        return UserService(db=self)
    
    # Add more services here
    @provider
    def provide_article_service(self) -> "ArticleService":
        return ArticleService()
```

## Example: Controller with Constructor Injection

```python
# myapp/controllers/user_controller.py
from ninja_extra import api_controller, route
from ninja_extra.schemas import NinjaAPIRequest
from ninja_extra.permissions import IsAuthenticated
from ninja import Schema
from injector import inject
from typing import List

class UserResponseSchema(Schema):
    id: int
    username: str
    email: str
    is_active: bool

@api_controller("/users", tags=['Users'])
class UserController:
    
    @inject
    def __init__(self, user_service: UserService):
        self.user_service = user_service
    
    @route.get("/", response=List[UserResponseSchema])
    def list_users(self):
        return self.user_service.get_all()
    
    @route.get("/{user_id}", response=UserResponseSchema)
    def get_user(self, user_id: int):
        return self.user_service.get_by_id(user_id)
    
    @route.post("/", response=UserResponseSchema)
    def create_user(self, data: UserCreateSchema):
        return self.user_service.create(
            username=data.username,
            email=data.email,
            password=data.password
        )
    
    @route.patch("/{user_id}", response=UserResponseSchema)
    def update_user(self, user_id: int, data: UserUpdateSchema):
        return self.user_service.update(
            user_id,
            **data.dict(exclude_unset=True)
        )
```

## Example: Multiple Services with Request Context

```python
# myapp/controllers/order_controller.py
from ninja_extra import api_controller, route
from ninja_extra.schemas import NinjaAPIRequest
from ninja_extra.permissions import IsAuthenticated
from ninja import Schema
from injector import inject
from typing import List

class OrderResponseSchema(Schema):
    id: int
    total: float
    status: str
    user_id: int

@api_controller("/orders", tags=['Orders'])
class OrderController:
    
    @inject
    def __init__(
        self,
        order_service: "OrderService",
        payment_service: "PaymentService",
        notification_service: "NotificationService",
        request: NinjaAPIRequest
    ):
        self.order_service = order_service
        self.payment_service = payment_service
        self.notification_service = notification_service
        self.request = request  # HTTP request context
    
    @route.get("/", response=List[OrderResponseSchema])
    def list_orders(self):
        return self.order_service.get_for_user(self.request.user)
    
    @route.post("/", response=OrderResponseSchema, permissions=[IsAuthenticated])
    def create_order(self, data: OrderCreateSchema):
        order = self.order_service.create(
            user=self.request.user,
            items=data.items
        )
        self.payment_service.process(order)
        self.notification_service.confirm_order(order)
        return order
```

## Example: Async Services with CDI

```python
# myapp/services/async_user_service.py
from typing import Protocol, List, AsyncIterator

class AsyncUserServiceProtocol(Protocol):
    async def get_by_id(self, user_id: int) -> "User": ...
    async def get_all(self) -> List["User"]: ...
    async def create(self, username: str, email: str) -> "User": ...

class AsyncUserService:
    def __init__(self, db: "Database"):
        self.db = db
    
    async def get_by_id(self, user_id: int) -> "User":
        return await self.db.async_get(User, id=user_id)
    
    async def get_all(self) -> List["User"]:
        return await self.db.async_query(User).all()
    
    async def create(self, username: str, email: str) -> "User":
        return await User.objects.acreate(username=username, email=email)

# Controller using async service
@api_controller("/async-users", tags=['Users'])
class AsyncUserController:
    
    @inject
    def __init__(self, async_user_service: AsyncUserService):
        self.async_user_service = async_user_service
    
    @route.get("/{user_id}")
    async def get_user(self, user_id: int):
        return await self.async_user_service.get_by_id(user_id)
```

## Example: Testing with Constructor Injection

```python
# tests/test_user_controller.py
from unittest.mock import Mock, MagicMock
import pytest

@pytest.fixture
def mock_user_service():
    service = Mock()
    service.get_by_id.return_value = User(id=1, username="test", email="test@test.com")
    service.get_all.return_value = [
        User(id=1, username="test1", email="test1@test.com"),
        User(id=2, username="test2", email="test2@test.com"),
    ]
    return service

def test_get_user_with_mocked_service(mock_user_service):
    controller = UserController(user_service=mock_user_service)
    result = controller.get_user(user_id=1)
    
    mock_user_service.get_by_id.assert_called_once_with(1)
    assert result.username == "test"

def test_list_users_with_mocked_service(mock_user_service):
    controller = UserController(user_service=mock_user_service)
    result = controller.list_users()
    
    mock_user_service.get_all.assert_called_once()
    assert len(result) == 2
```

## See Also

- [Knowledge: Constructor DI](../../knowledge/django-ninja/constructor-di.md)
- [Pattern: Class Controller Usage](../../patterns/django-ninja/class-controller-usage.md)
- [Pattern: JWT Auth Usage](../../patterns/django-ninja/jwt-auth-usage.md)
