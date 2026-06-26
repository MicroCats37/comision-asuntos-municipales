# TanStack Query v5: Migration Guide & Changes

## What is it
Summary of the most important breaking changes in v5 for API cleanup and better TypeScript support.

## Critical Changes
- **gcTime**: The old `cacheTime` is now `gcTime`.
- **Hook signatures**: Multiple separate arguments are no longer accepted. *Objects only*.
- **Removed Callbacks**: `onSuccess`, `onError`, `onSettled` removed from `useQuery`.
- **isPending**: The state `isLoading` is now `isPending` (to align with React Transitions). There is a new `isLoading` meaning `isPending && isFetching`.

## v4 vs v5 Comparison

```typescript
// ❌ v4 (Deprecated)
useQuery(['todos'], fetchTodos, { staleTime: 1000 });

// ✅ v5 (Modern)
useQuery({
  queryKey: ['todos'],
  queryFn: fetchTodos,
  staleTime: 1000,
});
```

## Gotchas
- If you used `onSuccess` to sync with a Zustand store, use a **Global Query Cache** or manage the transition in the consumer component.
- The new `isPending` can be tricky: it activates the first time data is loaded (no cache).