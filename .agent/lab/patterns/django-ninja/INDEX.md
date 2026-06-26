# Django Ninja Patterns Index

## PRIMARY Standard — django-ninja-extra

### Class Controller & Constructor DI Patterns
| Pattern | Context | When to Use |
|---------|---------|-------------|
| [class-controller-usage.md](./class-controller-usage.md) | `@api_controller` with routes | **PRIMARY** — All new endpoints |
| [constructor-di-usage.md](./constructor-di-usage.md) | `@inject` services | **PRIMARY** — Service injection |
| [jwt-auth-usage.md](./jwt-auth-usage.md) | JWT auth with `JWTAuth()` | **PRIMARY** — Authentication |

### Nested Relations & Batch Patterns
| Pattern | Context | When to Use |
|---------|---------|-------------|
| [nested-relations-usage.md](./nested-relations-usage.md) | `M2MDiffSchema` vs `BatchItemSchema` | **PRIMARY** — M2M for simple ID linking, Batch for nested CRUD |

### Functional Router Patterns (Alternative)
| Pattern | Context | When to Use |
|---------|---------|-------------|
| [di-service-usage.md](./di-service-usage.md) | `Depends()` injection | Legacy/simple endpoints |
| [schema-validation-usage.md](./schema-validation-usage.md) | Input/Output schema pairs | Request validation & response serialization |
| [selector-query-usage.md](./selector-query-usage.md) | Filtered, paginated queries | Data retrieval with composable filters |
| [testing-usage.md](./testing-usage.md) | TestClient with DI overrides | Endpoint testing with mocked dependencies |

## See Also
- [Knowledge: Django Ninja](../../knowledge/django-ninja/) — Concepts and references
- [Specs: Django Ninja](../../specs/django-ninja/)
