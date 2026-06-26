# Django Ninja: Selector Query Usage

## Context
Use selector classes to encapsulate query construction logic, making filtering and pagination reusable across endpoints and services.

## Recipe
```python
from ninja import Router
from sqlalchemy import select
from myapp.dependencies import get_db, get_product_selector
from myapp.models import Product
from myapp.schemas import ProductFilters, ProductResponse
from myapp.selectors import ProductSelector

product_router = Router(tags=["products"])

def get_product_selector(db=Depends(get_db)) -> ProductSelector:
    return ProductSelector(db=db)

@product_router.get("/", response=list[ProductResponse])
def list_products(
    request,
    filters: ProductFilters = Depends(),
    selector: Annotated[ProductSelector, Depends(get_product_selector)],
) -> list[Product]:
    query = selector.with_filters(filters)
    query = query.limit(filters.limit or 20).offset(filters.offset or 0)
    return list(request.db.execute(query).scalars())

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


# --- SELECTOR CLASS ---
class ProductSelector:
    def __init__(self, db):
        self.db = db

    def with_filters(self, filters: ProductFilters) -> Select[Product]:
        query = select(Product)
        if filters.category:
            query = query.where(Product.category == filters.category)
        if filters.min_price:
            query = query.where(Product.price >= filters.min_price)
        if filters.max_price:
            query = query.where(Product.price <= filters.max_price)
        if filters.search:
            query = query.where(Product.name.ilike(f"%{filters.search}%"))
        return query.order_by(Product.created_at.desc())

    def by_id(self, product_id: int) -> Product | None:
        return self.db.get(Product, product_id)
```

## Why This Way
Selectors separate query construction from business logic. Composable filter methods allow the same selector to build queries for list, search, and filter endpoints without duplicating where clauses.

## See Also
- [Knowledge: Selectors](../../knowledge/django-ninja/selectors.md)
- [Knowledge: Schemas](../../knowledge/django-ninja/schemas.md)
- [Spec: Project Structure](../../specs/django-ninja/project-structure/SPEC.md)
