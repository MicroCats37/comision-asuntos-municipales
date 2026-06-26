# Folder Structure — DDD/Hexagonal

Next.js project organized as Domain-Driven Design with Hexagonal Architecture layers.

## Rule

**REQUIRED**: All business logic lives in `src/core/`. Infrastructure adapters in `src/infra/`. Presentation in `src/app/`.

## Layer Diagram

```
src/
├── core/                    # DOMAIN — business logic, no framework imports
│   ├── entities/            # Pure TypeScript types/classes (User, Post, etc.)
│   ├── use-cases/           # Business operations (CreatePost, GetUser, etc.)
│   ├── repositories/        # Interface definitions (ports)
│   ├── errors/              # DomainError subclasses
│   └── types/               # Shared domain types (ErrorCode, ApiResponse, etc.)
│
├── infra/                   # INFRASTRUCTURE — framework adapters
│   ├── prisma/              # Prisma client, repository implementations
│   ├── auth/                # Auth.js configuration, callbacks
│   └── services/            # External adapters (email, storage)
│
└── app/                     # PRESENTATION — Next.js App Router
    ├── actions/             # Server Actions (entry points)
    ├── api/                 # Route Handlers (webhooks only)
    └── (routes)/            # Page routes with Server Components
```

## Layer Rules

### `src/core/` — Domain (Pure)

**REQUIRED**:
- Pure TypeScript with no Next.js, Prisma, or Auth.js imports
- Interfaces for repositories (ports)
- Domain entity types and business logic
- Error class hierarchy

**FORBIDDEN**:
- No `import from 'next'` or `import from 'next-auth'`
- No `import from '@prisma/client'`
- No direct database access

### `src/infra/` — Infrastructure (Adapters)

**REQUIRED**:
- Implements repository interfaces from `src/core/`
- Contains Prisma client, repository implementations
- Auth.js configuration and callbacks
- External service adapters

**FORBIDDEN**:
- Business logic (belongs in `src/core/use-cases/`)

### `src/app/` — Presentation (Next.js)

**REQUIRED**:
- Server Actions that delegate to use cases
- Server Components that fetch data
- Route Handlers only for external webhooks

**FORBIDDEN**:
- Business logic directly in actions or pages
- Prisma imports in Server Components (use repositories instead)

## Dependency Rules

```
src/app/ ──────────────► src/core/   (calls use-cases, uses types)
src/infra/ ───────────► src/core/   (implements interfaces)
src/app/ ──────────────► src/infra/ (uses injected dependencies)
```

**Important**: `src/core/` has no knowledge of `src/infra/` or `src/app/`.

## Example: Creating a Post

### `src/core/entities/post.ts`
```typescript
export interface Post {
  id: string;
  title: string;
  content: string;
  authorId: string;
  createdAt: Date;
}
```

### `src/core/repositories/post.repository.ts`
```typescript
import type { Post } from '@/core/entities/post';

export interface PostRepository {
  findById(id: string): Promise<Post | null>;
  create(data: { title: string; content: string; authorId: string }): Promise<Post>;
}
```

### `src/core/use-cases/create-post.ts`
```typescript
import type { PostRepository } from '@/core/repositories/post.repository';
import { ValidationError } from '@/core/errors';

export function createPost(
  repo: PostRepository,
  data: { title: string; content: string; authorId: string }
) {
  if (!data.title?.trim()) {
    throw new ValidationError('Title is required');
  }
  return repo.create(data);
}
```

### `src/infra/prisma/repositories/post.repository.ts`
```typescript
import { prisma } from '@/infra/prisma/client';
import type { PostRepository } from '@/core/repositories/post.repository';

export class PrismaPostRepository implements PostRepository {
  async findById(id: string) {
    return prisma.post.findUnique({ where: { id } });
  }
  async create(data) {
    return prisma.post.create({ data });
  }
}
```

### `src/app/actions/posts.ts`
```typescript
'use server';
import { createPost } from '@/core/use-cases/create-post';
import { prismaPostRepository } from '@/infra/prisma/repositories/post.repository';
import { revalidatePath } from 'next/cache';

export async function createPostAction(formData: FormData) {
  const title = formData.get('title') as string;
  const content = formData.get('content') as string;
  const authorId = formData.get('authorId') as string;
  
  const post = createPost(prismaPostRepository, { title, content, authorId });
  revalidatePath('/posts');
  return post;
}
```

## See Also

- [Specs: response-format.md](./response-format.md) — ApiResponse envelope
- [Specs: error-codes.md](./error-codes.md) — Error code definitions
- [Patterns: base-repository.md](../patterns/nextjs-backend/base-repository.md) — Repository pattern implementation