# Next.js Backend Patterns

Recipes showing how we integrate Auth.js, Prisma, and Server Actions in our Next.js backend stack.

## Contents

| Pattern | Description |
|---------|-------------|
| [with-auth.md](./with-auth.md) | `withAuth()` wrapper — role checking, session validation, error wrapping for Server Actions |
| [base-repository.md](./base-repository.md) | Generic `BaseRepository<T>` interface + Prisma implementation |
| [domain-error.md](./domain-error.md) | `DomainError`/`AppError` class hierarchy with error codes and HTTP mapping |
| [proxy-middleware.md](./proxy-middleware.md) | `middleware.ts` using `auth()` for route-level protection |

## See Also

- [Knowledge: authjs-setup](../knowledge/nextjs-backend/authjs-setup.md) — Auth.js v5 setup
- [Knowledge: server-actions](../knowledge/nextjs-backend/server-actions.md) — Server Action fundamentals
- [Specs: folder-structure](../specs/nextjs-backend/folder-structure.md) — DDD/Hexagonal layout