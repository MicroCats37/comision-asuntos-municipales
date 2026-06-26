# Server Actions

Server Actions are async functions that run on the server and can be invoked from client components or HTML forms. They replace traditional API routes for mutating data.

## Declaration

```typescript
'use server';
export async function myAction(formData: FormData) {
  // Runs on server only
}
```

The `'use server'` directive marks the file as Server Action exports. All exported functions in the file become Server Actions.

## Security Model

Server Actions ALWAYS execute on the server regardless of where they are called from. Client-side invocation is just a network request.

### Authorization is Mandatory

Every Server Action that mutates data must validate authorization:

```typescript
// src/app/actions/posts.ts
'use server';
import { auth } from '@/auth';
import { prisma } from '@/infra/prisma/client';
import { NotFoundError, PermissionDeniedError } from '@/core/errors';

export async function createPost(formData: FormData) {
  const session = await auth();
  if (!session?.user?.id) throw new PermissionDeniedError();
  
  const title = formData.get('title') as string;
  if (!title?.trim()) throw new ValidationError({ field: 'title' });
  
  return prisma.post.create({
    data: { title, authorId: session.user.id },
  });
}
```

## Form Actions

### HTML Form (Server Component)

```typescript
// src/app/posts/new/page.tsx
export default function NewPostPage() {
  return (
    <form action={createPost}>
      <input name="title" type="text" required />
      <textarea name="content" required />
      <button type="submit">Create Post</button>
    </form>
  );
}
```

### React useActionState (React 19)

```typescript
'use client';
import { useActionState } from 'react';
import { createPost } from '@/app/actions/posts';

export function PostForm() {
  const [state, formAction, isPending] = useActionState(createPost, null);
  
  return (
    <form action={formAction}>
      <input name="title" />
      {state?.error?.fieldErrors?.title && (
        <span>{state.error.fieldErrors.title}</span>
      )}
      <button disabled={isPending}>Submit</button>
    </form>
  );
}
```

## Revalidation

Server Actions that modify data should trigger revalidation:

```typescript
'use server';
import { revalidatePath } from 'next/cache';

export async function deletePost(postId: string) {
  // ... delete logic
  revalidatePath('/posts');
  revalidatePath('/posts/[id]', 'page');
}
```

## Server Actions vs Route Handlers

| Use Case | Approach |
|----------|----------|
| Form mutations (CRUD) | Server Actions |
| External API webhooks | Route Handlers (`app/api/`) |
| Streaming responses | Server Actions with `useActionState` |
| Binary file downloads | Route Handlers |
| Third-party webhook receivers | Route Handlers |

**Rule**: Default to Server Actions. Only use Route Handlers when you need to receive external webhooks or return raw binary responses.

## Error Handling

Server Actions should throw typed domain errors:

```typescript
'use server';
import { AppError } from '@/core/errors';

export async function updatePost(id: string, data: UpdatePostDTO) {
  const post = await prisma.post.findUnique({ where: { id } });
  if (!post) throw new NotFoundError('Post');
  
  if (!canEditPost(post)) throw new PermissionDeniedError();
  
  return prisma.post.update({ where: { id }, data });
}
```

The client receives these as JSON with the error code visible.

## Binding to Forms

### Progressive Enhancement

Server Actions work without JavaScript — form submits via traditional POST. This enables progressive enhancement.

```html
<form action={createPost}>
  <!-- Works with or without JS -->
</form>
```

### Form Validation

Client-side validation is optional but never sufficient. Always validate in the Server Action:

```typescript
'use server';
import { z } from 'zod';

const CreatePostSchema = z.object({
  title: z.string().min(1).max(200),
  content: z.string().min(1),
});

export async function createPost(prevState: unknown, formData: FormData) {
  const parsed = CreatePostSchema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) {
    return { success: false, error: { code: 'VALIDATION_ERROR', ... } };
  }
  // ... create logic
}
```

## See Also

- [Specs: validation](../specs/nextjs-backend/validation.md) — Zod schema validation in Server Actions
- [Patterns: withAuth](../patterns/nextjs-backend/with-auth.md) — Auth wrapper for Server Actions
- [Knowledge: authjs-setup](./authjs-setup.md) — Auth.js session handling