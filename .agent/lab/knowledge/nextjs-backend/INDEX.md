# Next.js Backend Knowledge

Technical facts and configuration reference for Next.js backend stack: Auth.js v5, Prisma, Server Actions, and RBAC.

## Contents

| File | Description |
|------|-------------|
| [authjs-setup.md](./authjs-setup.md) | Auth.js v5 + Prisma adapter, OAuth providers, JWT session strategy, role injection |
| [prisma-patterns.md](./prisma-patterns.md) | Prisma v6 config, schema conventions, migrations, seed scripts |
| [server-actions.md](./server-actions.md) | `use server` directive, form actions, revalidation, security model |
| [rbac-model.md](./rbac-model.md) | Role/Permission Prisma models, Auth.js session callbacks, middleware enforcement |
| [caching-revalidation.md](./caching-revalidation.md) | `revalidatePath`, `revalidateTag`, `unstable_cache` for cache invalidation |
| [file-uploads.md](./file-uploads.md) | Server Actions with FormData, presigned URLs for S3, file validation |
| [rate-limiting.md](./rate-limiting.md) | Middleware-based rate limiting, in-memory store, Upstash Redis for production |
| [webhooks.md](./webhooks.md) | Route Handlers for webhooks, HMAC signature verification, 200-fast pattern |
| [testing.md](./testing.md) | Vitest setup, testing Server Actions, Prisma + SQLite integration tests |

## Quick Reference

### Auth.js Session Callback (role injection)
```typescript
callbacks: {
  jwt({ token, user }) {
    if (user?.role) token.role = user.role;
    return token;
  },
  session({ session, token }) {
    if (token.role) session.user.role = token.role;
    return session;
  }
}
```

### Prisma Client Export
```typescript
import { PrismaClient } from '@/infra/prisma/client';
export const prisma = new PrismaClient();
```

### Server Action Declaration
```typescript
'use server';
export async function myAction(formData: FormData) { ... }
```

## See Also

- [Patterns: withAuth](../patterns/nextjs-backend/with-auth.md) — Server Action auth wrapper
- [Patterns: domainError](../patterns/nextjs-backend/domain-error.md) — Error class hierarchy
- [Specs: folder-structure](../specs/nextjs-backend/folder-structure.md) — DDD/Hexagonal layout
