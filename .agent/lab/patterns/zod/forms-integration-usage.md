# Zod: Form Integration (React Hook Form)

## Context
Standard for all Platform Foundation forms, ensuring type safety from input to database.

## Recipe
```typescript
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { UserSchema } from './schemas/user-schema';
import { useActionState } from 'react';

// Server Action
async function updateUser(prevState: unknown, formData: FormData) {
  'use server';
  const validated = UserSchema.parse(Object.fromEntries(formData));
  await db.user.update(validated);
  return { success: true };
}

// Form Component
function UserForm({ userId }: { userId: string }) {
  const [error, formAction, isPending] = useActionState(updateUser, null);
  
  const form = useForm({
    resolver: zodResolver(UserSchema),
    defaultValues: { userId },
  });

  return (
    <form action={formAction}>
      <input {...form.register('username')} />
      {form.formState.errors.username && (
        <span>{form.formState.errors.username.message}</span>
      )}
      <button type="submit" disabled={isPending}>
        {isPending ? 'Saving...' : 'Save'}
      </button>
    </form>
  );
}
```

## Why This Way
Zod + React Hook Form + useActionState creates a type-safe chain from UI input to server validation. The resolver handles client-side validation while useActionState manages server-side submission state.

## See Also
- [Knowledge: Form Integration](../../knowledge/zod/forms-integration.md)
- [Spec: Forms SPEC](../../specs/nextjs/forms/SPEC.md)
