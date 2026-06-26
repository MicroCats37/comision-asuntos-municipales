# Master Specs Index

This directory contains **architectural contracts** — the source of truth for what we've decided to build.

## 🚦 Quick Navigation

| Spec Domain | Entry Point | Description |
|-------------|-------------|-------------|
| **Django Ninja** | [django-ninja/INDEX.md](./django-ninja/INDEX.md) | DDD-lite: Services, Schemas, DI, Routers, API structure, error handling |
| **Next.js** | [nextjs/INDEX.md](./nextjs/INDEX.md) | App Router, Server Components, Actions |
| **Next.js Backend** | [nextjs-backend/INDEX.md](./nextjs-backend/INDEX.md) | DDD/Hexagonal, response format, error codes, validation |
| **Shared Contracts** | [shared/](./shared/) | Cross-cutting specs (API format, error handling, types) |

## Spec Structure (3-File Pattern)

Each spec domain follows a **3-file triad** pattern:

| File | Purpose |
|------|---------|
| `SPEC.md` | Rules, `REQUIRED`/`FORBIDDEN` patterns, architectural decisions |
| `IO.md` | Pydantic schemas, data contracts, type signatures |
| `EXAMPLES.md` | Runnable code examples for each documented pattern |

## Governance

- **Specs are source-of-truth** for AI agents — they override general patterns.
- Each spec MUST have `❌ FORBIDDEN` and `✅ REQUIRED` sections.
- Refer to `../../knowledge/` for fundamental concepts before reading specs.
- Each spec MUST link to worked examples in `EXAMPLES.md`.

## Adding Specs

1. Create the spec domain directory (e.g., `django-ninja/`)
2. Create the 3-file triad structure for each spec topic
3. Update this master INDEX.md with the new spec domain
4. Keep specs focused — one topic per spec directory

## See Also

- [Knowledge Layer](../knowledge/) — WHAT each technology is
- [Patterns Layer](../patterns/) — HOW we use each technology
- [Projects Layer](../projects/) — Project-specific overrides
