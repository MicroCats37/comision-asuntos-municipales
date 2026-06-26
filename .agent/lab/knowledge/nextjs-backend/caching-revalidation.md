# Caching & Revalidation

Next.js provides multiple layers of cache invalidation. Use the right mechanism for your use case.

## `revalidatePath(path)` — Single Route Purge

Purges the Next.js Data Cache for a specific route. Next request triggers a fresh render.

```typescript
'use server';
import { revalidatePath } from 'next/cache';
import { updatePost } from '@/core/posts/actions';

export async function publishPost(postId: string) {
  await updatePost(postId, { published: true });
  revalidatePath(`/posts/${postId}`);
  revalidatePath('/posts'); // also update the list page
}
```

**When to use**: One specific page changed (e.g., a blog post was updated).

---

## `revalidateTag(tag)` — Cross-Page Cache Invalidation

Tags group related cached data. A single tag can span multiple pages.

```typescript
'use server';
import { revalidateTag } from 'next/cache';
import { createComment } from '@/core/comments/actions';

export async function addComment(postId: string, formData: FormData) {
  const comment = await createComment({ postId, content: formData.get('content') });
  revalidateTag(`post-${postId}`); // invalidates all pages that use this tag
}
```

In a Server Component:
```typescript
// fetch with tag
const post = await fetch(`https://api.example.com/posts/${id}`, {
  next: { tags: [`post-${id}`] }
});
```

**When to use**: Related data appears on multiple pages (e.g., comments on a post that shows on both the post page and the author's profile).

---

## `unstable_cache(fn, keyParts, { tags, revalidate })` — Query-Level Caching

Wraps any function (typically a DB query) with automatic revalidation.

```typescript
import { unstable_cache } from 'next/cache';
import { prisma } from '@/infra/prisma/client';

const getPostWithAuthor = unstable_cache(
  async (postId: string) => prisma.post.findUnique({
    where: { id: postId },
    include: { author: true }
  }),
  ['post-with-author'],          // cache key parts
  { tags: ['posts'], revalidate: 60 } // 60-second TTL
);

export { getPostWithAuthor };
```

**When to use**: Expensive DB queries that should be cached and only re-fetched after mutations.

---

## Decision Matrix

| Mechanism | Scope | Use When |
|----------|-------|----------|
| `revalidatePath` | Single route | A specific page changed |
| `revalidateTag` | Any route using the tag | Data shared across multiple pages |
| `unstable_cache` | Function result | Expensive queries need caching + auto-revalidation |

---

## Server Action Pattern with Revalidation

```typescript
'use server';
import { revalidatePath, revalidateTag } from 'next/cache';
import { createPost } from '@/core/posts/actions';
import { FormState } from '@/lib/actions/form-state';

export async function createPostAction(prev: FormState, formData: FormData): Promise<FormState> {
  try {
    const post = await createPost({
      title: formData.get('title') as string,
      content: formData.get('content') as string,
    });
    revalidatePath('/posts');
    revalidateTag('posts');
    return { status: 'success', data: post };
  } catch (e) {
    return { status: 'error', message: e instanceof Error ? e.message : 'Failed' };
  }
}
```

---

## On-Demand vs Time-Based

- **On-demand** (`revalidatePath`/`revalidateTag`): Triggered by mutations via Server Actions.
- **Time-based** (`revalidate` option): Automatic expiration after N seconds.

Prefer on-demand for data correctness; use time-based as a safety net for stale data.
