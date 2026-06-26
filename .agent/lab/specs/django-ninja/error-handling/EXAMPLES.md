# Error Handling: Worked Examples

## Example 1: Custom Exception Handler

```python
from ninja import NinjaAPI
from ninja.jwt_auth import AuthBearer
from myapp.exceptions import (
    AppException, ProductNotFoundError,
    ValidationError, PermissionDeniedError,
)

api = NinjaAPI(urls_path="api/v1", auth=AuthBearer())

@api.exception_handler(AppException)
def handle_app_exception(request, exc: AppException):
    return api.create_response(
        request,
        {
            "message": exc.message,
            "code": exc.code,
            "field_errors": exc.field_errors,
        },
        status=exc.status_code,
    )

# All AppException subclasses are now handled automatically
```

## Example 2: Using Exceptions in Services

```python
class ProductService:
    def __init__(self, db):
        self.db = db

    def get_by_id(self, product_id: int) -> Product:
        product = self.db.get(Product, product_id)
        if not product:
            raise ProductNotFoundError(f"Product {product_id} not found")
        return product

    def create(self, data: ProductCreate) -> Product:
        # Domain validation
        if self._product_exists_by_name(data.name):
            raise ConflictError(f"Product with name '{data.name}' already exists")
        product = Product(**data.model_dump())
        self.db.add(product)
        self.db.commit()
        return product

    def _product_exists_by_name(self, name: str) -> bool:
        return (
            self.db.query(Product)
            .filter(Product.name == name)
            .first()
        ) is not None
```

## Example 3: ValidationError with Field Errors

```python
class OrderService:
    def create(self, data: OrderCreate) -> Order:
        field_errors: dict[str, list[str]] = {}

        if data.quantity <= 0:
            field_errors.setdefault("quantity", []).append("Must be greater than 0")

        if data.product_id and not self._product_exists(data.product_id):
            field_errors.setdefault("product_id", []).append("Product does not exist")

        if field_errors:
            raise ValidationError(
                message="Validation failed",
                field_errors=field_errors,
            )

        return self._create_order(data)

    def _product_exists(self, product_id: int) -> bool:
        return self.db.get(Product, product_id) is not None
```

## Example 4: Testing Error Responses

```python
from ninja.testing import TestClient

client = TestClient(api)

def test_product_not_found():
    response = client.get("/products/99999")
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "PRODUCT_NOT_FOUND"
    assert "not found" in data["message"].lower()

def test_validation_error():
    response = client.post("/products/", json={"name": "", "price": "-1"})
    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert "field_errors" in data
    assert "name" in data["field_errors"]
```

## See Also
- [Spec: Error Handling](./SPEC.md)
- [Knowledge: Testing](../../knowledge/django-ninja/testing.md)
- [Shared: Django Error Handling](../shared/django-error-handling.md)
