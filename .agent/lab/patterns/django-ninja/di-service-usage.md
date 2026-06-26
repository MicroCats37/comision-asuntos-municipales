# Django Ninja: DI Service Usage

## Context
Inject service classes into routers using `Depends()` to keep business logic out of the HTTP layer and enable testability via dependency overrides.

## Recipe
```python
from ninja import Router
from typing import Annotated
from myapp.dependencies import get_db, get_product_service
from myapp.schemas import ProductCreate, ProductResponse

product_router = Router(tags=["products"])

def get_product_service(db=Depends(get_db)) -> ProductService:
    return ProductService(db=db)

@product_router.get("/", response=list[ProductResponse])
def list_products(
    request,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> list[Product]:
    return service.list()

@product_router.post("/", response=ProductResponse)
def create_product(
    request,
    data: ProductCreate,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> Product:
    return service.create(data)

@product_router.get("/{product_id}", response=ProductResponse)
def get_product(
    request,
    product_id: int,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> Product:
    return service.get_by_id(product_id)

@product_router.delete("/{product_id}", response=ProductResponse)
def delete_product(
    request,
    product_id: int,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> Product:
    return service.delete(product_id)
```

## Why This Way
Using `Annotated[...]` with `Depends()` gives precise type hints for IDE support. The dependency factory pattern (`get_product_service`) keeps the service instantiation logic reusable and testable. Overriding the dependency in tests lets us inject mocks without touching the router.

## See Also
- [Knowledge: Dependency Injection](../../knowledge/django-ninja/dependency-injection.md)
- [Knowledge: Services](../../knowledge/django-ninja/services.md)
- [Spec: Project Structure](../../specs/django-ninja/project-structure/SPEC.md)
