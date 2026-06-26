# TanStack Query v5: Core Patterns & queryOptions

## What is it
Version 5 standardizes all hook calls to use **exclusively the object syntax**, removing overloaded signatures. Introduces `queryOptions` to share query definitions between client and server with perfect typing.

## Golden Rules
- ✅ DO: Always use the object syntax `{ queryKey, queryFn }`.
- ✅ DO: Define queries using the `queryOptions` helper for reuse in `useQuery`, `prefetchQuery`, and `ensureQueryData`.
- ❌ DON'T: Attempt to pass separate arguments (e.g., `useQuery(key, fn)`); this will cause an error in v5.

## Canonical Code

```typescript
import { useQuery, queryOptions } from '@tanstack/react-query';

// 1. Centralized Definition (The Gold Standard)
export const userOptions = (userId: string) => 
  queryOptions({
    queryKey: ['users', userId],
    queryFn: () => fetchUser(userId),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

// 2. Component Consumption
function UserProfile({ id }: { id: string }) {
  const { data, isLoading } = useQuery(userOptions(id));
  
  if (isLoading) return <div>Loading...</div>;
  return <div>{data.name}</div>;
}
```

## Gotchas
- The old `cacheTime` is now called **`gcTime`** (Garbage Collection Time).
- `onSuccess`, `onError`, and `onSettled` callbacks are no longer available in `useQuery`. Handle these effects in `useEffect` or via `queryClient.setQueryData`.


