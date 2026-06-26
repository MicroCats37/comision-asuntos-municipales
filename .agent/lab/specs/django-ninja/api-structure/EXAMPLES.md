# API Structure: Worked Examples

## Example 1: Full CRUD Router

```python
from ninja import Router, NinjaAPI
from typing import Annotated
from myapp.dependencies import get_db, get_product_service, get_product_selector
from myapp.schemas import (
    ProductCreate, ProductUpdate, ProductResponse,
    ProductFilters, PaginatedProductResponse,
)
from myapp.services import ProductService
from myapp.selectors import ProductSelector

product_router = Router(tags=["products"])

def get_product_service(db=Depends(get_db)) -> ProductService:
    return ProductService(db=db)

def get_product_selector(db=Depends(get_db)) -> ProductSelector:
    return ProductSelector(db=db)

@product_router.get("/", response=PaginatedProductResponse)
def list_products(
    request,
    filters: ProductFilters = Depends(),
    selector: Annotated[ProductSelector, Depends(get_product_selector)],
) -> PaginatedProductResponse:
    query = selector.with_filters(filters)
    total = selector.count_with_filters(filters)
    query = query.limit(filters.page_size).offset((filters.page - 1) * filters.page_size)
    items = list(request.db.execute(query).scalars())
    total_pages = (total + filters.page_size - 1) // filters.page_size
    return PaginatedProductResponse(
        items=[ProductResponse.model_validate(p) for p in items],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
        total_pages=total_pages,
    )

@product_router.get("/{product_id}", response=ProductResponse)
def get_product(
    request,
    product_id: int,
    selector: Annotated[ProductSelector, Depends(get_product_selector)],
) -> Product:
    product = selector.by_id(product_id)
    if not product:
        raise ProductNotFoundError(product_id)
    return product

@product_router.post("/", response=ProductResponse, status_code=201)
def create_product(
    request,
    data: ProductCreate,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> Product:
    return service.create(data)

@product_router.patch("/{product_id}", response=ProductResponse)
def update_product(
    request,
    product_id: int,
    data: ProductUpdate,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> Product:
    product = service.update(product_id, data)
    if not product:
        raise ProductNotFoundError(product_id)
    return product

@product_router.delete("/{product_id}", status_code=204)
def delete_product(
    request,
    product_id: int,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> None:
    service.delete(product_id)

# Mount at API
api = NinjaAPI(urls_path="api/v1")
api.add_router("/products", product_router)
```

## Example 2: Nested Router (Sub-resources)

```python
order_router = Router(tags=["orders"])
order_item_router = Router(tags=["order-items"])

@order_router.get("/{order_id}/items", response=list[OrderItemResponse])
def list_order_items(request, order_id: int) -> list[OrderItem]:
    ...

@order_router.post("/{order_id}/items", response=OrderItemResponse, status_code=201)
def create_order_item(request, order_id: int, data: OrderItemCreate) -> OrderItem:
    ...

api = NinjaAPI(urls_path="api/v1")
api.add_router("/orders", order_router)
api.add_router("/orders", order_item_router)  # nested under /orders
```

## See Also
- [Spec: API Structure](./SPEC.md)
- [Spec: Error Handling](../error-handling/SPEC.md)
