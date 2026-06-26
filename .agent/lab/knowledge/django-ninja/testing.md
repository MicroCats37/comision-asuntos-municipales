# Django Ninja: Testing

## Overview
`ninja.testing.TestClient` provides a synchronous test client for Django Ninja endpoints. It simulates HTTP requests without running a live server, enabling fast unit and integration tests.

## Key Concepts
- **TestClient**: `ninja.testing.TestClient` wraps the NinjaAPI for testing.
- **Request kwargs**: Pass path params, query params, and body as kwargs.
- **assert_json_response()**: Check response status and JSON body.
- **Testing with DI**: Override dependencies via `client=TestClient(api, overrides={...})`.

## When to Use
For testing API endpoints, validating schema serialization, and integration testing with overridden dependencies (mocks, in-memory DBs).

## Testing Anatomy
```python
from ninja.testing import TestClient
from myapp.api import api

client = TestClient(api)

# GET request
response = client.get("/products/")
assert response.status_code == 200
data = response.json()
assert len(data) == 3

# POST request
response = client.post("/products/", json={"name": "Widget", "price": "9.99"})
assert response.status_code == 201
product = response.json()
assert product["id"] is not None

# With overrides (DI mock)
from unittest.mock import MagicMock
mock_service = MagicMock(spec=ProductService)
mock_service.list.return_value = []

client = TestClient(api, overrides={
    Depends(get_product_service): lambda: mock_service
})
response = client.get("/products/")
assert response.status_code == 200
```

## See Also
- [Pattern: Testing Usage](../../patterns/django-ninja/testing-usage.md)
- [Spec: API Structure](../../specs/django-ninja/api-structure/SPEC.md)
