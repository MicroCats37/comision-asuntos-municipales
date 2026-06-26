# Django Ninja: Dependency Injection

## Overview
Django Ninja's `Depends()` provides per-request dependency injection. Dependencies are resolved for each request, allowing services and other objects to access request-scoped context (db session, auth info, etc.).

## Key Concepts
- **`Depends()`**: Declares a dependency that Ninja resolves before calling the endpoint.
- **Per-request lifetime**: Each request gets a fresh instance of the dependency.
- **Callable dependencies**: Any callable (class, function, generator) can be a dependency.
- **Generator dependencies**: Use generators for setup/teardown (e.g., opening/closing db transactions).
- **Parameter source**: `Depends()` params come from the request; regular params come from the URL/body.

## When to Use
Whenever an endpoint needs access to services, database sessions, authentication, or any object that should be created per-request.

## DI Anatomy
```python
from ninja import Router
from ninja.jwt_auth import AuthBearer
from ninja.orm import Factory

# Database session as a dependency
def get_db(request):
    db = request.db
    try:
        yield db
    finally:
        pass  # transaction committed via middleware

# Service injection
def get_product_service(db=Depends(get_db)) -> ProductService:
    return ProductService(db=db)

@product_router.get("/{product_id}", response=ProductResponse)
def get_product(
    request,
    product_id: int,
    service: ProductService = Depends(get_product_service)
) -> Product:
    return service.get_by_id(product_id)
```

## See Also
- [Pattern: DI Service Usage](../../patterns/django-ninja/di-service-usage.md)
- [Spec: Error Handling](../../specs/django-ninja/error-handling/SPEC.md)
