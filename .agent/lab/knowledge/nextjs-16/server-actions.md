# Next.js 16: Server Actions & Mutations

## What is it
Async functions executed on the server but callable from the client. They replace traditional API endpoints for data mutations.

## Golden Rules
- ✅ DO: Use `useActionState` in the client to manage the Server Action lifecycle.
- ✅ DO: Validate data with **Zod** within the action before processing.
- ❌ DON'T: Forget `revalidatePath` or `revalidateTag` after a successful mutation.

## Canonical Code

```tsx
// app/actions.ts
'use server'
import { revalidatePath } from 'next/cache';
import { schema } from './schema';

export async function createItem(prevState: any, formData: FormData) {
  const validated = schema.safeParse(Object.fromEntries(formData));
  if (!validated.success) return { error: 'Invalid data' };

  await db.item.create({ data: validated.data });
  revalidatePath('/items');
  return { success: true };
}

// ui/form.tsx (Client)
'use client'
import { useActionState } from 'react';
import { createItem } from '@/app/actions';

export function MyForm() {
  const [state, formAction, isPending] = useActionState(createItem, null);
  
  return (
    <form action={formAction}>
      <input name="name" />
      <button disabled={isPending}>Create</button>
      {state?.error && <p>{state.error}</p>}
    </form>
  );
}
```

## Gotchas
- Server Actions only return serializable data.
- Always use `redirect` outside of `try/catch` as it uses an internal exception flow.