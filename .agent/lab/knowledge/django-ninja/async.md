# Django Ninja: Async

## Overview
Django Ninja supports async views and ORM access via `sync_to_async`. Sync views can call async code, and async views can use Django's sync ORM with `sync_to_async` wrapper.

## Key Concepts
- **Async views**: Declare with `async def`; use `await` for async operations.
- **`sync_to_async`**: Wraps sync ORM calls to run in an async executor.
- **Async ORM**: For high-concurrency APIs, use `asyncpg` with Django's async ORM.
- **Performance**: Async shines for I/O-bound operations (external API calls, DB queries with latency).

## When to Use
For high-throughput APIs where blocking on I/O limits concurrency. For typical CRUD APIs, sync views with a connection pool are sufficient and simpler.

## Async Anatomy
```python
from asgiref.sync import sync_to_async
from ninja import Router

async_router = Router(tags=["async-products"])

# Async endpoint with sync_to_async wrapper
@async_router.get("/", response=list[ProductResponse])
async def list_products_async(request) -> list[Product]:
    # Run sync ORM call in async executor
    products = await sync_to_async(list)(
        Product.objects.all()
    )
    return products

# Or use async ORM with asyncpg
@async_router.post("/", response=ProductResponse)
async def create_product_async(request, data: ProductCreate) -> Product:
    product = await Product.objects.acreate(**data.model_dump())
    return product
```

## See Also
- [Knowledge: Services](./services.md)
- [Spec: Project Structure](../../specs/django-ninja/project-structure/SPEC.md)
