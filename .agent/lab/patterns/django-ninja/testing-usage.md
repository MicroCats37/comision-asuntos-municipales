# Django Ninja: Testing Usage

## Context
Use `ninja.testing.TestClient` to test endpoints with dependency overrides, enabling in-memory mocks without database or external service dependencies.

## Recipe
```python
from ninja.testing import TestClient
from myapp.api import api
from myapp.dependencies import get_product_service, get_db
from myapp.schemas import ProductCreate, ProductResponse

client = TestClient(api)

# --- Basic endpoint tests ---

def test_list_products():
    response = client.get("/products/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_create_product():
    response = client.post("/products/", json={
        "name": "Test Widget",
        "price": "19.99",
        "category": "TOOLS",
    })
    assert response.status_code == 201
    product = response.json()
    assert product["id"] is not None
    assert product["name"] == "Test Widget"

def test_get_product():
    # Create first
    create_response = client.post("/products/", json={
        "name": "Fetch Test",
        "price": "9.99",
        "category": "ELECTRONICS",
    })
    product_id = create_response.json()["id"]

    # Then fetch
    response = client.get(f"/products/{product_id}")
    assert response.status_code == 200
    assert response.json()["id"] == product_id

def test_get_product_not_found():
    response = client.get("/products/99999")
    assert response.status_code == 404

# --- With DI overrides (mock service) ---

from unittest.mock import MagicMock, AsyncMock
from myapp.services import ProductService

def test_list_products_with_mock():
    mock_service = MagicMock(spec=ProductService)
    mock_service.list.return_value = []

    override_client = TestClient(api, overrides={
        get_product_service: lambda: mock_service,
    })

    response = override_client.get("/products/")
    assert response.status_code == 200
    mock_service.list.assert_called_once()

def test_create_product_with_mock():
    mock_service = MagicMock(spec=ProductService)
    mock_service.create.return_value = MagicMock(
        id=1, name="Mock", price=MagicMock(), category="MOCK"
    )

    override_client = TestClient(api, overrides={
        get_product_service: lambda: mock_service,
    })

    response = override_client.post("/products/", json={
        "name": "Mock Product",
        "price": "10.00",
        "category": "MOCK",
    })
    assert response.status_code == 201
    mock_service.create.assert_called_once()
```

## Why This Way
`TestClient` runs requests against the NinjaAPI without a live server. Overrides let us inject mock services to test business logic in isolation. This avoids database setup/teardown in unit tests while still validating the full request-to-response path.

## See Also
- [Knowledge: Testing](../../knowledge/django-ninja/testing.md)
- [Knowledge: Dependency Injection](../../knowledge/django-ninja/dependency-injection.md)
- [Spec: API Structure](../../specs/django-ninja/api-structure/SPEC.md)
