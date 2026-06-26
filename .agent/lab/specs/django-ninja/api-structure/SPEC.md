# API Structure Spec

## Rule
All endpoints MUST use the `{verb}/{resource}` naming convention with a leading `/api/v{major}` version prefix. Routers organize endpoints by domain and MUST be mounted at the API root.

## Context
Consistent API structure makes the interface predictable. Versioning allows backward-incompatible changes without breaking existing clients. Router-based organization mirrors Django app boundaries.

---

## Endpoint Naming

### ✅ REQUIRED

| Pattern | Example | Use For |
|---------|---------|---------|
| `GET /api/v1/products/` | List products | Collection listing |
| `GET /api/v1/products/{id}` | Get single product | Retrieve by ID |
| `POST /api/v1/products/` | Create product | Creating new resources |
| `PUT /api/v1/products/{id}` | Full update | Replacing a resource |
| `PATCH /api/v1/products/{id}` | Partial update | Updating specific fields |
| `DELETE /api/v1/products/{id}` | Delete product | Removing a resource |

### ❌ FORBIDDEN

| Pattern | Why |
|---------|-----|
| `GET /api/v1/listProducts` | Must use plural nouns, no verbs in resource names |
| `POST /api/v1/products/create` | POST itself is the "create" verb |
| `GET /api/v1/products/filter` | Filter params go in query string, not path |

---

## Versioning

### ✅ REQUIRED
- Major version in URL path: `/api/v1/`, `/api/v2/`
- Use `APIV1` or `APIV2` as the `NinjaAPI` url path prefix
- Deprecate older versions with a `Deprecation` response header

### ❌ FORBIDDEN
- No version in body or headers only (URL is the source of truth for versioning)
- No breaking changes within a major version

---

## Router Organization

### ✅ REQUIRED
- One `Router` per Django app or logical domain
- Router `tags=["..."]` MUST match the domain name
- Mount routers with `api.add_router("/products", product_router)`

### ❌ FORBIDDEN
- Monolithic single router for the entire API
- Different routers for the same resource (e.g., admin vs public)

---

## Request/Response Conventions

### ✅ REQUIRED
- All responses MUST be wrapped in the standard `ApiResponse[T]` envelope (yielding `{success, data, error}`).
- Use `response=ApiResponse[list[T]]` or `response=ApiResponse[T]` to declare the generic schema natively for Swagger.
- Pagination uses cursor or offset-based with `page`/`page_size` query params, wrapped in `PaginatedApiResponse[T]`.

### ❌ FORBIDDEN
- Returning naked schemas without the `ApiResponse` wrapper.
- Using verb-based endpoint names

---

## Decision Log
- **v1.0**: Initial spec — adopted `/api/v{version}` URL versioning with NinjaAPI prefix
- **v1.0**: Router tags mirror domain names for OpenAPI grouping
