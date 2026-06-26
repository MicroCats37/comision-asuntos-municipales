# RBAC Model

Role-Based Access Control using Prisma models and Auth.js session callbacks.

## Data Model

### Prisma Schema

```prisma
model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  role      String   @default("user")
  createdAt DateTime @default(now())
  // ... other fields
}

model Post {
  id        String   @id @default(cuid())
  title     String
  content   String
  authorId  String
  author    User     @relation(...)
  
  @@index([authorId])
}
```

### Role Hierarchy

| Role | Permissions |
|------|-------------|
| `admin` | Full access to all resources |
| `editor` | Create/edit own posts, view all |
| `user` | View content, edit own profile |
| `guest` | View published content only |

Roles are stored as strings on the User model. For more complex systems, add a Role/Permission model.

### Extended RBAC (Optional)

```prisma
model Role {
  id          String   @id @default(cuid())
  name        String   @unique
  permissions Permission[]
  users       User[]
}

model Permission {
  id     String @id @default(cuid())
  name   String @unique
  roles  Role[]
}
```

## Auth.js Session Callbacks

```typescript
// auth.ts
export const authConfig = {
  callbacks: {
    async jwt({ token, user }) {
      if (user?.id) token.sub = user.id;
      if (user?.role) token.role = user.role;
      return token;
    },
    async session({ session, token }) {
      if (token.sub) session.user.id = token.sub;
      if (token.role) session.user.role = token.role;
      return session;
    },
  },
} satisfies NextAuthConfig;
```

Session type extension in `types/next-auth.d.ts`:

```typescript
import type { DefaultSession } from 'next-auth';

declare module 'next-auth' {
  interface Session {
    user: {
      id: string;
      role: string;
    } & DefaultSession['user'];
  }
}
```

## Permission Checking

### In Server Actions

```typescript
'use server';
import { auth } from '@/auth';
import { PermissionDeniedError } from '@/core/errors';

export async function deletePost(postId: string) {
  const session = await auth();
  
  if (!session?.user?.id) throw new PermissionDeniedError();
  
  const post = await prisma.post.findUnique({ where: { id: postId } });
  if (!post) throw new NotFoundError('Post');
  
  // Admin can delete any post; others only their own
  const canDelete = session.user.role === 'admin' || post.authorId === session.user.id;
  if (!canDelete) throw new PermissionDeniedError();
  
  return prisma.post.delete({ where: { id: postId } });
}
```

### Role Checking Utility

```typescript
// src/core/auth/roles.ts
const ROLE_HIERARCHY: Record<string, number> = {
  guest: 0,
  user: 1,
  editor: 2,
  admin: 3,
};

export function hasRole(userRole: string, requiredRole: string): boolean {
  return (ROLE_HIERARCHY[userRole] ?? 0) >= (ROLE_HIERARCHY[requiredRole] ?? 0);
}

export function requireRole(userRole: string, requiredRole: string): void {
  if (!hasRole(userRole, requiredRole)) {
    throw new PermissionDeniedError();
  }
}
```

## Middleware Protection

```typescript
// middleware.ts
import { auth } from '@/auth';

export default auth((req) => {
  const pathname = req.nextUrl.pathname;
  
  // Protect admin routes
  if (pathname.startsWith('/admin')) {
    if (req.auth?.user?.role !== 'admin') {
      return Response.redirect(new URL('/unauthorized', req.url));
    }
  }
});

export const config = {
  matcher: ['/admin/:path*'],
};
```

## See Also

- [Patterns: withAuth](../patterns/nextjs-backend/with-auth.md) — withAuth() Server Action wrapper
- [Patterns: proxyMiddleware](../patterns/nextjs-backend/proxy-middleware.md) — Route protection middleware
- [Specs: error-codes](../specs/nextjs-backend/error-codes.md) — PERMISSION_DENIED error definition