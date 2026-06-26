# TanStack Query v5: Suspense Integration

## What is it
A first-class API that allows components to "suspend" while data is loading, delegating the loading state to a parent `Suspense` component.

## Golden Rules
- ✅ DO: Use `useSuspenseQuery` instead of `useQuery` when you want React to handle the loading state automatically.
- ✅ DO: Ensure the component is wrapped in a `<Suspense fallback={...}>`.
- ❌ DON'T: Use `useSuspenseQuery` if you need granular loading state management within the same component (e.g., local mini-spinner).

## Canonical Code

```typescript
import { useSuspenseQuery } from '@tanstack/react-query';
import { userOptions } from './queries';

function UserProfile({ id }) {
  // TS knows 'data' is NEVER undefined here
  const { data } = useSuspenseQuery(userOptions(id));

  return <h1>{data.name}</h1>;
}

// In the parent:
<Suspense fallback={<Skeleton />}>
  <UserProfile id="123" />
</Suspense>
```

## Gotchas
- `useSuspenseQuery` returns `data` directly, eliminating `isLoading` from destructuring.
- If the query fails, it will throw an error to be caught by an **ErrorBoundary**.