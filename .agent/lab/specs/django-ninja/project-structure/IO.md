# Project Structure: Inputs & Outputs — Hexagonal Architecture

## Schema Naming (Presentation & Domain)

```python
# presentation/schemas.py OR domain/schemas.py

# Input schemas (request)
class ProductCreateIn(Schema): ...
class ProductUpdateIn(Schema): ...
class ProductFiltersIn(Schema): ...

# Output schemas (response)
class ProductOut(Schema): ...
class ProductListOut(Schema): ...
class ErrorOut(Schema): ...
```

## Domain Interfaces (Ports)

```python
# domain/interfaces.py
from typing import Protocol

class IProductRepository(Protocol):
    def save(self, data: dict) -> dict: ...
    def get_by_id(self, product_id: int) -> dict | None: ...
    def delete(self, product_id: int) -> bool: ...

class IProductSelector(Protocol):
    def with_filters(self, filters: dict) -> list[dict]: ...
```

## Service Interface (Domain)

```python
# domain/services.py
from ninja_extra.di import inject
from .interfaces import IProductRepository, IProductSelector

class ProductService:
    @inject
    def __init__(self, repo: IProductRepository, selector: IProductSelector):
        self.repo = repo
        self.selector = selector

    def create(self, data: dict) -> dict: ...
    def get_by_id(self, product_id: int) -> dict | None: ...
    def list(self, filters: dict) -> list[dict]: ...
```

## Concrete Implementations (Infrastructure)

```python
# infrastructure/repositories.py
from ..domain.interfaces import IProductRepository
from .models import ProductORM

class DjangoProductRepository(IProductRepository):
    def save(self, data: dict) -> dict: ...
    def get_by_id(self, product_id: int) -> dict | None: ...
    def delete(self, product_id: int) -> bool: ...
```

## Controller Interface (Presentation)

```python
# presentation/controllers.py
from ninja_extra import api_controller, route
from ninja_extra.di import inject
from ..domain.services import ProductService
from .schemas import ProductOut, ProductCreateIn

@api_controller('/products', tags=["products"])
class ProductController:
    @inject
    def __init__(self, service: ProductService):
        self.service = service

    @route.get("/", response=list[ProductOut])
    def list_products(self, ...) -> list[dict]: ...

    @route.post("/", response=ProductOut, status_code=201)
    def create_product(self, payload: ProductCreateIn) -> dict: ...
```

## DI Container Setup (Core)

```python
# core/di.py
from ninja_extra import injector
from myapp.domain.interfaces import IProductRepository, IProductSelector
from myapp.infrastructure.repositories import DjangoProductRepository
from myapp.infrastructure.selectors import DjangoProductSelector

def setup_injection():
    injector.binder.bind(IProductRepository, to=DjangoProductRepository)
    injector.binder.bind(IProductSelector, to=DjangoProductSelector)
```

## See Also
- [Spec: Project Structure](./SPEC.md)
- [Knowledge: Hexagonal Architecture](../../../knowledge/django-ninja/hexagonal-architecture.md)