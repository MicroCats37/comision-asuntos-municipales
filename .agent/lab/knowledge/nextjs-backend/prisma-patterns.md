# Prisma Patterns

Prisma v6 ORM for type-safe database access in Next.js, configured for PostgreSQL (production) and SQLite (development).

## Configuration

### `prisma/schema.prisma`

```prisma
generator client {
  provider = "prisma-client-js"
  output   = "../src/infra/prisma/generated"
}

datasource db {
  provider = "sqlite" // or "postgresql" for production
  url      = env("DATABASE_URL")
}

model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  role      String   @default("user")
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  // ... domain fields
}

model Post {
  id        String   @id @default(cuid())
  title     String
  content   String
  published Boolean  @default(false)
  authorId  String
  author    User     @relation(fields: [authorId], references: [id])
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}
```

### `prisma.config.ts` (Prisma v6)

```typescript
import { defineConfig } from 'prisma/config';

export default defineConfig({
  earlyAccess: true,
  schema: './prisma/schema.prisma',
});
```

### `package.json` scripts

```json
{
  "db:migrate": "prisma migrate dev",
  "db:push": "prisma db push",
  "db:generate": "prisma generate",
  "db:seed": "tsx prisma/seed.ts",
  "db:studio": "prisma studio"
}
```

## Client Export

### `src/infra/prisma/client.ts`

```typescript
import { PrismaClient } from '../generated/client';

const globalForPrisma = globalThis as unknown as { prisma: PrismaClient };

export const prisma =
  globalForPrisma.prisma ||
  new PrismaClient({
    log: process.env.NODE_ENV === 'development' ? ['query', 'error', 'warn'] : ['error'],
  });

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma;
```

## Migrations

```bash
# Create migration
npx prisma migrate dev --name add_user_role

# Apply migrations in production
npx prisma migrate deploy

# Reset database (dev only)
npx prisma migrate reset
```

## Seed Script

### `prisma/seed.ts`

```typescript
import { PrismaClient } from './src/infra/prisma/generated/client';

const prisma = new PrismaClient();

async function main() {
  const user = await prisma.user.upsert({
    where: { email: 'admin@example.com' },
    update: {},
    create: {
      email: 'admin@example.com',
      name: 'Admin',
      role: 'admin',
    },
  });
  console.log({ user });
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
```

## PrismaClient in Server Actions

Never instantiate PrismaClient inside Server Actions directly. Use the exported singleton:

```typescript
import { prisma } from '@/infra/prisma/client';

// ✅ Correct — uses singleton
export async function getPosts() {
  return prisma.post.findMany({ where: { published: true } });
}

// ❌ Wrong — creates new instance each time
export async function getPosts() {
  const localPrisma = new PrismaClient(); // Don't do this
}
```

## Type Generation

After schema changes:

```bash
npx prisma generate
```

This regenerates `src/infra/prisma/generated/client.ts` with updated types.

## Indexes

Add indexes for foreign keys and frequently queried fields:

```prisma
model Post {
  authorId String
  author   User   @relation(...)
  
  @@index([authorId])
}
```

## See Also

- [Patterns: baseRepository](../patterns/nextjs-backend/base-repository.md) — Generic repository wrapper
- [Knowledge: authjs-setup](./authjs-setup.md) — Auth.js PrismaAdapter integration