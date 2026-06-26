# Next.js Backend Specs

Architectural contracts for the Next.js backend stack: DDD/Hexagonal folder structure, response format, error codes, and validation.

## Contents

| Spec | Description |
|------|-------------|
| [folder-structure.md](./folder-structure.md) | DDD/Hexagonal layout: `src/core/`, `src/infra/`, `src/app/` with REQUIRED/FORBIDDEN rules |
| [response-format.md](./response-format.md) | Unified `ApiResponse<T>` envelope: `{ success, data, error, meta }` |
| [error-codes.md](./error-codes.md) | Error code registry identical to Django: NOT_FOUND, VALIDATION_ERROR, etc. |
| [validation.md](./validation.md) | Zod `safeParse` in Server Actions, field error mapping |

## See Also

- [Patterns: withAuth](../patterns/nextjs-backend/with-auth.md) — withAuth() wrapper implementation
- [Patterns: domainError](../patterns/nextjs-backend/domain-error.md) — Error class hierarchy
- [Specs: shared/api-format.md](../shared/api-format.md) — Cross-cutting API format (same as Django)