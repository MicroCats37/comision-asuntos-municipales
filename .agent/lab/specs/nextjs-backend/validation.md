# Validation — Zod in Server Actions

Zod schemas validate all input in Server Actions before business logic executes.

## Rule

**REQUIRED**: All Server Actions with form input MUST validate using Zod `safeParse` and return typed `ValidationError` with field mapping.

## Schema Definition

### `src/app/actions/_lib/schemas.ts`

```typescript
import { z } from 'zod';

export const CreatePostSchema = z.object({
  title: z.string().min(1, 'Title is required').max(200, 'Title too long'),
  content: z.string().min(1, 'Content is required'),
  published: z.boolean().optional().default(false),
});

export const UpdatePostSchema = z.object({
  title: z.string().min(1).max(200).optional(),
  content: z.string().min(1).optional(),
  published: z.boolean().optional(),
});

export const PaginationSchema = z.object({
  page: z.coerce.number().int().positive().default(1),
  pageSize: z.coerce.number().int().min(1).max(100).default(20),
});

export type CreatePostDTO = z.infer<typeof CreatePostSchema>;
export type UpdatePostDTO = z.infer<typeof UpdatePostSchema>;
```

## Validation in Server Actions

### Basic Pattern

```typescript
// src/app/actions/posts.ts
'use server';
import { CreatePostSchema } from './_lib/schemas';
import { ValidationError, NotFoundError } from '@/core/errors';

export async function createPostAction(prevState: unknown, formData: FormData) {
  // Parse form data
  const rawData = Object.fromEntries(formData.entries());
  const parsed = CreatePostSchema.safeParse(rawData);
  
  if (!parsed.success) {
    const fieldErrors = parsed.error.flatten().fieldErrors;
    return {
      success: false,
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Validation failed',
        details: { fieldErrors },
      },
    };
  }
  
  // Validation passed — proceed with business logic
  const post = await postRepository.create(parsed.data);
  revalidatePath('/posts');
  
  return { success: true, data: post, error: null };
}
```

### With `useActionState` (React 19)

```typescript
'use client';
import { useActionState } from 'react';
import { createPostAction } from '@/app/actions/posts';

export function PostForm() {
  const [state, formAction, isPending] = useActionState(createPostAction, null);
  
  return (
    <form action={formAction}>
      <input name="title" placeholder="Post title" />
      {state?.error?.details?.fieldErrors?.title && (
        <span>{state.error.details.fieldErrors.title[0]}</span>
      )}
      <textarea name="content" />
      <button type="submit" disabled={isPending}>Create</button>
    </form>
  );
}
```

## Field Error Mapping

Zod's `flatten().fieldErrors` produces:

```typescript
{
  title: ['Title is required', 'Title too long'],
  content: ['Content is required']
}
```

This maps directly to `ValidationError.fieldErrors`:

```typescript
const fieldErrors = parsed.error.flatten().fieldErrors;
throw new ValidationError('Validation failed', fieldErrors);
```

## Validation in Use Cases

For cleaner separation, validation can happen at use case level:

```typescript
// src/core/use-cases/create-post.ts
import type { PostRepository } from '@/core/repositories/post.repository';
import { ValidationError } from '@/core/errors';
import type { CreatePostDTO } from '@/app/actions/_lib/schemas';

export function createPost(repo: PostRepository, data: CreatePostDTO) {
  // Business logic validation
  if (data.title.toLowerCase().includes('spam')) {
    throw new BusinessError('Post title contains disallowed content');
  }
  return repo.create(data);
}
```

## See Also

- [Specs: error-codes.md](./error-codes.md) — VALIDATION_ERROR code definition
- [Specs: response-format.md](./response-format.md) — ApiResponse envelope
- [Patterns: domainError.md](../patterns/nextjs-backend/domain-error.md) — Error class with fieldErrors