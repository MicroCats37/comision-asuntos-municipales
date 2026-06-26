# Django Ninja: Routers

## Overview
Routers organize endpoints into logical groups. Django Ninja provides `NinjaAPI` for the root API and `Router` for grouping related endpoints. Routes are decorated with `@router.get()`, `@router.post()`, etc.

## Key Concepts
- **NinjaAPI**: The main API instance — the root router that collects all routes.
- **Router**: A sub-router that groups related endpoints (e.g., `/products`, `/orders`).
- **Decorators**: `@router.get()`, `@router.post()`, `@router.put()`, `@router.delete()`, `@router.patch()`.
- **Path parameters**: Type-annotated function parameters become path/query/body params automatically.

## When to Use
To organize endpoints by domain. Each Django app or logical domain should have its own `Router`.

## Router Anatomy
```python
from ninja import Router, NinjaAPI

product_router = Router(tags=["products"])

@product_router.get("/", response=list[ProductResponse])
def list_products(request, filters: ProductFilters = Depends()) -> list[Product]:
    service = ProductService(db=request.db)
    selector = ProductSelector(db=request.db)
    query = selector.with_filters(filters)
    return list(request.db.execute(query).scalars())

@product_router.post("/", response=ProductResponse)
def create_product(request, data: ProductCreate) -> Product:
    service = ProductService(db=request.db)
    return service.create(data)

api = NinjaAPI()
api.add_router("/products", product_router)
```

## See Also
- [Pattern: DI Service Usage](../../patterns/django-ninja/di-service-usage.md)
- [Spec: API Structure](../../specs/django-ninja/api-structure/SPEC.md)
