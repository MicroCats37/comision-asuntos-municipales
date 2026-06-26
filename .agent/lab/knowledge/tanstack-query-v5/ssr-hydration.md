# TanStack Query v5: SSR & Hydration (Next.js)

## What is it
A pattern for fetching data on the server (Server Components) and passing it to the client transparently, ensuring the user sees the data immediately on first render.

## Golden Rules
- ✅ DO: Use one `QueryClient` per request on the server.
- ✅ DO: Wrap client components in a `HydrationBoundary`.
- ❌ DON'T: Pass data manually through props if you can use Hydration; hydration keeps the cache warm for future navigations.

## Canonical Code

```tsx
// app/posts/page.tsx (Server Component)
import { dehydrate, HydrationBoundary, QueryClient } from '@tanstack/react-query';
import Posts from './posts'; // Client Component

export default async function PostsPage() {
  const queryClient = new QueryClient();

  await queryClient.prefetchQuery({
    queryKey: ['posts'],
    queryFn: getPosts,
  });

  return (
    // 'dehydrate' serializes the server cache for the client
    <HydrationBoundary state={dehydrate(queryClient)}>
      <Posts />
    </HydrationBoundary>
  );
}
```

## Gotchas
- The `QueryClient` on the server must be created **inside** the component function or via a helper to avoid data leakage between users.
- Ensure `queryKey` matches exactly between server and client.