# withAuth — Server Action Auth Wrapper

## Context

Server Actions need consistent auth checking and role validation before executing business logic. `withAuth()` wraps actions to inject session validation and role checking.

## Recipe

```typescript
// src/app/actions/_lib/with-auth.ts
import { auth } from '@/auth';
import { PermissionDeniedError } from '@/core/errors';

type ActionFn<T = unknown> = () => T | Promise<T>;

export function withAuth<T>(
  action: ActionFn<T>,
  requiredRole?: string
): () => Promise<T> {
  return async () => {
    const session = await auth();
    
    if (!session?.user?.id) {
      throw new PermissionDeniedError('Authentication required');
    }
    
    if (requiredRole && session.user.role !== requiredRole) {
      if (session.user.role !== 'admin') {
        throw new PermissionDeniedError(`Role '${requiredRole}' required`);
      }
    }
    
    return action();
  };
}

// Convenience wrapper for form actions with FormData
export function withAuthForm<T>(
  action: (formData: FormData) => Promise<T>,
  requiredRole?: string
) {
  return async (prevState: unknown, formData: FormData): Promise<T> => {
    const session = await auth();
    
    if (!session?.user?.id) {
      throw new PermissionDeniedError('Authentication required');
    }
    
    if (requiredRole && session.user.role !== requiredRole) {
      if (session.user.role !== 'admin') {
        throw new PermissionDeniedError(`Role '${requiredRole}' required`);
      }
    }
    
    return action(formData);
  };
}
```

## Usage

```typescript
// src/app/actions/posts.ts
'use server';
import { withAuth, withAuthForm } from './_lib/with-auth';
import { prisma } from '@/infra/prisma/client';
import { revalidatePath } from 'next/cache';

export const createPost = withAuthForm(async (formData: FormData) => {
  const title = formData.get('title') as string;
  const content = formData.get('content') as string;
  
  const post = await prisma.post.create({
    data: { title, content, authorId: auth().user.id },
  });
  
  revalidatePath('/posts');
  return { id: post.id };
}, 'user');

export const deletePost = withAuth(async () => {
  // ... delete logic
  revalidatePath('/posts');
}, 'admin');
```

## Why This Way

- Centralizes auth validation — no forgotten checks in individual actions
- Role checking is explicit at call site
- Wrapped actions throw typed errors that the envelope format handles

## See Also

- [Knowledge: authjs-setup](../../knowledge/nextjs-backend/authjs-setup.md) — Auth.js session callbacks
- [Knowledge: rbac-model](../../knowledge/nextjs-backend/rbac-model.md) — Role hierarchy
- [Specs: error-codes](../../specs/nextjs-backend/error-codes.md) — PERMISSION_DENIED definition