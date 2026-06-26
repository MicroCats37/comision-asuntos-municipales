# BaseRepository — Generic Prisma Repository

## Context

We need consistent CRUD patterns across domain entities. `BaseRepository<T>` provides a generic interface that Prisma implementations must satisfy.

## Recipe

### Interface

```typescript
// src/core/repositories/base.repository.ts
export interface BaseRepository<T, CreateDTO, UpdateDTO> {
  findById(id: string): Promise<T | null>;
  findAll(options?: { page?: number; pageSize?: number }): Promise<{ data: T[]; total: number }>;
  create(data: CreateDTO): Promise<T>;
  update(id: string, data: UpdateDTO): Promise<T>;
  delete(id: string): Promise<T>;
}
```

### Prisma Implementation

```typescript
// src/infra/prisma/repositories/post.repository.ts
import { prisma } from '@/infra/prisma/client';
import type { BaseRepository } from '@/core/repositories/base.repository';
import type { Post, Prisma } from '@/infra/prisma/generated/client';

export interface PostDTO {
  title: string;
  content: string;
  authorId: string;
}

export interface PostUpdateDTO {
  title?: string;
  content?: string;
  published?: boolean;
}

export class PostRepository implements BaseRepository<Post, PostDTO, PostUpdateDTO> {
  async findById(id: string): Promise<Post | null> {
    return prisma.post.findUnique({ where: { id } });
  }

  async findAll({ page = 1, pageSize = 20 }: { page?: number; pageSize?: number } = {}): Promise<{ data: Post[]; total: number }> {
    const skip = (page - 1) * pageSize;
    const [data, total] = await Promise.all([
      prisma.post.findMany({ skip, take: pageSize, orderBy: { createdAt: 'desc' } }),
      prisma.post.count(),
    ]);
    return { data, total };
  }

  async create(data: PostDTO): Promise<Post> {
    return prisma.post.create({ data });
  }

  async update(id: string, data: PostUpdateDTO): Promise<Post> {
    return prisma.post.update({ where: { id }, data });
  }

  async delete(id: string): Promise<Post> {
    return prisma.post.delete({ where: { id } });
  }
}

export const postRepository = new PostRepository();
```

### Usage in Server Actions

```typescript
// src/app/actions/posts.ts
'use server';
import { postRepository } from '@/infra/prisma/repositories/post.repository';

export async function getPosts(page = 1) {
  return postRepository.findAll({ page, pageSize: 20 });
}

export async function getPost(id: string) {
  const post = await postRepository.findById(id);
  if (!post) throw new NotFoundError('Post');
  return post;
}
```

## Why This Way

- Interface defined in `src/core/` (no Prisma imports)
- Implementation in `src/infra/` (framework details)
- Easy to mock for testing
- Consistent CRUD signature across entities

## See Also

- [Specs: folder-structure](../../specs/nextjs-backend/folder-structure.md) — Layer separation rules
- [Knowledge: prisma-patterns](../../knowledge/nextjs-backend/prisma-patterns.md) — Prisma client setup