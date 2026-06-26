# TanStack Query v5: Core Patterns & queryOptions

## Context
The bridge between Axios (our fetcher) and Global State. It syncs with React 19 Suspense for clean data loading.

## Recipe
```typescript
import { useQuery, queryOptions } from '@tanstack/react-query';
import { api } from './axios-instance';
import { UserSchema } from './zod/user-schema';

// Centralized query definition
export const userOptions = (userId: string) => 
  queryOptions({
    queryKey: ['users', userId],
    queryFn: async () => {
      const { data } = await api.get(`/users/${userId}`);
      return UserSchema.parse(data); // Validate response with Zod
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

// Component with Suspense
function UserProfile({ id }: { id: string }) {
  const { data } = useQuery(userOptions(id));
  
  return <div>{data.name}</div>;
}

// Prefetch in Server Component
export default async function UserPage({ params }: { params: { id: string } }) {
  const queryClient = await getQueryClient();
  
  await queryClient.prefetchQuery(userOptions(params.id));
  
  return (
    <HydrationBoundary state={queryClient dehydrateState}>
      <UserProfile id={params.id} />
    </HydrationBoundary>
  );
}
```

## Why This Way
queryOptions centralizes query configuration, making it reusable across useQuery, prefetchQuery, and ensureQueryData. Zod validation on the response ensures type safety from API to component.

## See Also
- [Knowledge: Core Patterns](../../knowledge/tanstack-query-v5/core-patterns.md)
- [Spec: Forms IO](../../specs/nextjs/forms/IO.md)
