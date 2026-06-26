# TanStack Query v5: Mutations & Invalidation

## What is it
A mechanism for making server changes (POST, PUT, DELETE) and automatically synchronizing the local cache to ensure the UI reflects changes immediately.

## Golden Rules
- ✅ DO: Invalidate related queries in the mutation's `onSuccess` callback.
- ✅ DO: Use `mutateAsync` only when you need manual promise handling (e.g., complex `try/catch`).
- ❌ DON'T: Forget the exact `queryKey` when invalidating; if the key doesn't match, data will stay stale.

## Canonical Code

```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query';

export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (newUser: CreateUserDto) => api.post('/users', newUser),
    onSuccess: () => {
      // Invalidate the users list to force a refetch
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (error) => {
      console.error("Error creating user", error);
    }
  });
}
```

## Gotchas
- Unlike `useQuery`, mutations **DO** retain `onSuccess`, `onError`, and `onSettled` callbacks in v5.
- If you invalidate a query not currently in use, it will simply be marked "stale" and refetched next time it's used.