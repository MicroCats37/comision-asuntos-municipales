# Proxy Middleware — Route Protection

## Context

Next.js middleware protects routes at the edge before rendering. We use Auth.js `auth()` to validate sessions and redirect unauthorized users.

## Recipe

### `middleware.ts` (root of `src/app/`)

```typescript
import { auth } from '@/auth';

export default auth((req) => {
  const { pathname } = req.nextUrl;
  
  // Public paths that don't require auth
  const publicPaths = ['/', '/login', '/register', '/auth/error'];
  if (publicPaths.some(p => pathname.startsWith(p))) {
    return;
  }
  
  // Check auth status
  if (!req.auth) {
    const loginUrl = new URL('/login', req.url);
    loginUrl.searchParams.set('callbackUrl', pathname);
    return Response.redirect(loginUrl);
  }
  
  // Role-based protection
  if (pathname.startsWith('/admin') && req.auth.user?.role !== 'admin') {
    return Response.redirect(new URL('/unauthorized', req.url));
  }
  
  // Dashboard requires authentication
  if (pathname.startsWith('/dashboard') && !req.auth.user?.id) {
    return Response.redirect(new URL('/login', req.url));
  }
});

export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)',
  ],
};
```

## How It Works

1. **Edge execution**: Middleware runs before any page renders
2. **Session check**: `auth()` from Auth.js reads the session cookie
3. **Redirect**: Unauthenticated users are sent to `/login`
4. **Matcher**: Only intercepts specified paths

## Public Paths Configuration

```typescript
// Pattern: allowlist vs blocklist
const publicPaths = [
  '/',                        // Home page
  '/login',                   // Auth pages
  '/register',
  '/auth/error',
  '/posts/public',            // Public posts list
];

const protectedPaths = [
  '/admin/:path*',            // Admin panel (role-protected)
  '/dashboard/:path*',        // User dashboard
  '/settings/:path*',        // User settings
];
```

## Multiple Middleware Exports

For complex apps, export named config:

```typescript
import { auth } from '@/auth';

export default auth((req) => {
  // Main auth logic
});

export const adminMiddleware = auth((req) => {
  if (req.auth?.user?.role !== 'admin') {
    return Response.redirect(new URL('/unauthorized', req.url));
  }
});
```

## Why This Way

- Runs at the edge — faster than checking auth in Server Components
- Single source of truth for route protection
- Declarative — auth rules visible at top level

## See Also

- [Knowledge: authjs-setup](../../knowledge/nextjs-backend/authjs-setup.md) — Auth.js configuration
- [Knowledge: rbac-model](../../knowledge/nextjs-backend/rbac-model.md) — Role hierarchy
- [Patterns: withAuth](./with-auth.md) — Server Action auth wrapper (complementary)