# Project Structure Spec — Hexagonal Architecture

## Rule
All Django Ninja apps using django-ninja-extra MUST follow **Hexagonal Architecture** (Ports & Adapters). Each app is organized into domain/, infrastructure/, presentation/, and core/ layers. Dependencies flow inward: presentation -> domain <- infrastructure.

## Context
Hexagonal Architecture separates business logic (domain) from infrastructure concerns (persistence, external APIs) and HTTP concerns (presentation). This enables testability, maintainability, and the ability to swap infrastructure implementations without touching domain logic.

---

## Folder Structure

### REQUIRED - Hexagonal Layer Structure

myapp/
├── __init__.py
├── domain/                  # BUSINESS LOGIC - NO INFRASTRUCTURE DEPENDENCIES
│   ├── __init__.py
│   ├── models.py            # Domain entities (Pydantic or Django ORM)
│   ├── schemas.py           # Domain schemas (input/output validation)
│   ├── services.py          # Business logic classes
│   ├── selectors.py         # Query factory interfaces (ports)
│   ├── repositories.py     # Repository interfaces (ports)
│   └── exceptions.py        # Domain exceptions
│
├── infrastructure/          # ADAPTERS - IMPLEMENTATIONS
│   ├── __init__.py
│   ├── repositories.py      # Repository implementations (Django ORM, SQLAlchemy)
│   ├── selectors.py        # Concrete selector implementations
│   └── services.py          # Infrastructure service implementations (email, cache, etc.)
│
├── presentation/             # ADAPTERS - HTTP
│   ├── __init__.py
│   ├── controllers.py      # django-ninja-extra api_controller classes
│   ├── routers.py           # Ninja Router definitions
│   ├── dependencies.py      # Depends() factories + injector module
│   └── urls.py             # api.add_router() calls
│
└── core/                    # SHARED ACROSS ALL APPS
    ├── __init__.py
    ├── config.py            # Settings and configuration
    ├── exceptions.py       # Shared AppException hierarchy
    └── pagination.py        # Pagination utilities

### FORBIDDEN
- Domain importing from infrastructure or presentation (dependency rule violation)
- Infrastructure importing from presentation (HTTP leaks into persistence)
- Business logic in presentation/controllers.py (keep thin - orchestrate only)
- Mixing domain entities with infrastructure concerns

---

## Layer Dependencies

presentation -> domain <- infrastructure
                   |
                core (shared)

Presentation Layer (HTTP):
  - Controllers call domain services
  - Routers map HTTP endpoints to controller methods
  - Dependencies inject domain services via factory functions

Domain Layer (Pure Business Logic):
  - Services contain all business rules
  - Selectors define query interfaces (ports)
  - Repositories define persistence interfaces (ports)
  - Exceptions represent business rule violations

Infrastructure Layer (External Concerns):
  - Repositories implement data persistence
  - Selectors implement concrete queries
  - Infrastructure services implement external integrations (email, SMS, cache)
  - Depends on domain interfaces, not concrete implementations

Core Layer (Shared):
  - Contains shared utilities, exceptions, pagination
  - No domain knowledge, no layer-specific logic
  - `core/types.py` — `BaseSchema`, `AsForm`, `hydrate_form` (import from here, never reimplement)
  - `core/responses.py` — `ApiResponse[T]`, `PaginatedApiResponse[T]`, `success_response`, `error_response`
  - `core/models/` — `BaseModel` (UUID + timestamps)

### REQUIRED
- Domain services import only from domain/ (schemas, models, exceptions, selectors, repositories)
- Infrastructure imports domain interfaces and implements them
- Presentation imports domain services and infrastructure implementations
- Core contains only shared utilities with NO domain knowledge
- **All schemas MUST inherit from `core.types.BaseSchema`**, never from `ninja.Schema` directly
- **All schemas MUST use `pydantic.Field(..., description="...")`** on every field

### FORBIDDEN
- Domain layer depending on infrastructure (ORM, external APIs)
- Domain layer depending on presentation (HTTP concerns)
- Infrastructure accessing presentation directly

---

## File Naming Conventions

| Layer | File | Export | Content |
|-------|------|--------|---------|
| domain | schemas.py | EntityOperationIn, EntityOperationOut | Pydantic schemas |
| domain | services.py | EntityService | Business logic interface |
| domain | selectors.py | EntitySelector | Query interface (port) |
| domain | repositories.py | EntityRepository | Persistence interface (port) |
| infrastructure | repositories.py | EntityRepositoryImpl | Concrete persistence implementation |
| infrastructure | selectors.py | EntitySelectorImpl | Concrete query implementation |
| infrastructure | services.py | EntityInfrastructureService | External integrations |
| presentation | controllers.py | EntityController | django-ninja-extra controller |
| presentation | routers.py | entity_router | Ninja Router |

### FORBIDDEN
- Selectors in domain/ containing SQL (belongs in infrastructure/)
- Business logic in infrastructure/ (belongs in domain/)
- Concrete implementations in domain/ (belongs in infrastructure/)

---

## django-ninja-extra Conventions

### REQUIRED
- Use @api_controller for class-based controllers with django-ninja-extra
- Use @route decorators on controller methods
- Use @inject from injector for constructor dependency injection
- Register exception handlers on the NinjaAPI instance
- Use Depends() for cross-cutting concerns (db, auth)

### FORBIDDEN
- Using function-based views for API endpoints with django-ninja-extra
- Mixing functional routers with class controllers in the same app
- Direct ORM queries in controllers (delegate to domain services)

---

## Decision Log
- v2.0: Migrated from DDD-lite (flat structure) to Hexagonal Architecture (layered)
- v2.0: Added domain/, infrastructure/, presentation/, core/ layers
- v2.0: Domain layer is pure Python - no Django or ORM imports
- v2.0: Infrastructure contains concrete implementations (repositories, external services)
- v2.0: Presentation layer uses django-ninja-extra class controllers

## See Also
- [Bounded Context Spec](./bounded-context/SPEC.md) — 1 App = 1 Bounded Context rule and internal folder structure
- [Response Envelope Knowledge](../../knowledge/django-ninja/response-envelope.md) — Standard `ApiResponse` format
