# Auth.js v5 Setup

Auth.js v5 (formerly NextAuth.js) provides authentication for Next.js with support for OAuth providers, JWT sessions, and database adapters.

## Architecture

Auth.js v5 sits between the presentation layer (`src/app/`) and infrastructure (`src/infra/`). It uses:
- **Providers**: OAuth credentials (Google, GitHub) or email magic links
- **PrismaAdapter**: Links Auth.js to Prisma for account/user storage
- **JWT Strategy**: Sessions stored as signed tokens (stateless), roles injected via callbacks

```
┌─────────────────────────────────────────────────────┐
│  src/app/ (Server Actions, Pages)                  │
├─────────────────────────────────────────────────────┤
│  Auth.js — auth(), signIn(), signOut()              │
├─────────────────────────────────────────────────────┤
│  PrismaAdapter → src/infra/prisma/                  │
└─────────────────────────────────────────────────────┘
```

## Installation

```bash
npm install next-auth@beta @auth/prisma-adapter
```

## Configuration

### `auth.ts` (root)

```typescript
import { PrismaAdapter } from '@auth/prisma-adapter';
import Google from 'next-auth/providers/google';
import type { NextAuthConfig } from 'next-auth';
import { prisma } from '@/infra/prisma/client';

export const authConfig = {
  adapter: PrismaAdapter(prisma),
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  session: { strategy: 'jwt' },
  pages: {
    signIn: '/login',
    error: '/auth/error',
  },
  callbacks: {
    // Inject role from database into JWT token
    async jwt({ token, user }) {
      if (user?.id) token.sub = user.id;
      if (user?.role) token.role = user.role;
      return token;
    },
    // Expose role to session (available in client/server components)
    async session({ session, token }) {
      if (token.sub) session.user.id = token.sub;
      if (token.role) session.user.role = token.role;
      return session;
    },
  },
} satisfies NextAuthConfig;
```

### `auth/index.ts` (re-export)

```typescript
export { handlers, auth, signIn, signOut } from 'next-auth';
```

## Prisma Schema Requirements

Auth.js PrismaAdapter expects these models (extend from your User model):

```prisma
model User {
  id            String    @id @default(cuid())
  email         String    @unique
  name          String?
  image         String?
  role          String    @default("user")
  emailVerified DateTime?
  accounts      Account[]
  sessions      Session[]
  // ... your domain fields
}

model Account {
  userId          String
  type            String
  provider        String
  providerAccountId String
  refresh_token   String?   @db.Text
  access_token    String?   @db.Text
  expires_at      Int?
  token_type      String?
  scope           String?
  id_token        String?   @db.Text
  session_state   String?
  user            User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  @@id([provider, providerAccountId])
}

model Session {
  sessionToken String   @unique
  userId       String
  expires      DateTime
  user         User     @relation(fields: [userId], references: [id], onDelete: Cascade)
}
```

## Environment Variables

```env
AUTH_SECRET=your-secret-key  # openssl rand -base64 32
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
NEXTAUTH_URL=http://localhost:3000
```

## Usage in Server Components

```typescript
// src/app/dashboard/page.tsx
import { auth } from '@/auth';
import { redirect } from 'next/navigation';

export default async function DashboardPage() {
  const session = await auth();
  if (!session) redirect('/login');
  
  return (
    <div>
      <p>Welcome {session.user?.name}</p>
      <p>Role: {session.user?.role}</p>
    </div>
  );
}
```

## Usage in Server Actions

```typescript
// src/app/actions/settings.ts
'use server';
import { auth } from '@/auth';

export async function updateProfile(formData: FormData) {
  const session = await auth();
  if (!session?.user?.id) throw new Error('Unauthorized');
  // ... update logic
}
```

## OAuth vs Credentials

| Provider Type | Use Case | Session Strategy |
|---------------|----------|-----------------|
| OAuth (Google, GitHub) | Social login | JWT with PrismaAdapter |
| Credentials | Email/password | JWT only (no PrismaAdapter needed) |

For credentials provider with bcrypt password hashing, omit `adapter` and use JWT strategy only.

## See Also

- [Patterns: withAuth](../patterns/nextjs-backend/with-auth.md) — Role-based Server Action guard
- [Patterns: proxyMiddleware](../patterns/nextjs-backend/proxy-middleware.md) — Route-level protection
- [Knowledge: rbac-model](./rbac-model.md) — Role/Permission schema