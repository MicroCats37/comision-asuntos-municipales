# Django Ninja Specs Index

## Core Specifications
| Spec | Focus | Files |
|------|-------|-------|
| [API Structure](./api-structure/SPEC.md) | Endpoint naming, versioning, router organization | [Spec](./api-structure/SPEC.md) · [IO](./api-structure/IO.md) · [Examples](./api-structure/EXAMPLES.md) |
| [Error Handling](./error-handling/SPEC.md) | Exception handlers, error schema | [Spec](./error-handling/SPEC.md) · [IO](./error-handling/IO.md) · [Examples](./error-handling/EXAMPLES.md) |
| [Project Structure](./project-structure/SPEC.md) | DDD-lite folder layout per Django app | [Spec](./project-structure/SPEC.md) · [IO](./project-structure/IO.md) · [Examples](./project-structure/EXAMPLES.md) |
| [Bounded Context](./bounded-context/SPEC.md) | 1 App = 1 Bounded Context, domain/infrastructure/presentation layers | [Spec](./bounded-context/SPEC.md) · [IO](./bounded-context/IO.md) · [Examples](./bounded-context/EXAMPLES.md) |
| [File Uploads](./file-uploads/SPEC.md) | AsForm + hydrate_form pattern for typed file endpoints | [Spec](./file-uploads/SPEC.md) · [IO](./file-uploads/IO.md) · [Examples](./file-uploads/EXAMPLES.md) |

## Cross-Cutting Contracts
| Contract | Scope | Files |
|----------|-------|-------|
| [Django API Format](../shared/django-api-format.md) | ApiResponse envelope, BaseSchema, null/blank contract | [Contract](../shared/django-api-format.md) |
| [Django Error Handling](./django-error-handling.md) | Django Ninja exception strategy | [Contract](./django-error-handling.md) |

## Spec File Structure (3-File Pattern)
Each spec contains exactly three files:
| File | Purpose |
|------|---------|
| `SPEC.md` | Rules, REQUIRED/FORBIDDEN patterns, architectural decisions |
| `IO.md` | Pydantic schemas, data contracts, type signatures |
| `EXAMPLES.md` | Runnable code examples for each documented pattern |

## Governance
- All specs follow the **Django Ninja + DDD-lite** standard.
- Specs are source-of-truth for the AI.
- Refer to `../../knowledge/` for fundamental concepts.
- Each spec MUST have `❌ FORBIDDEN` and `✅ REQUIRED` sections.
