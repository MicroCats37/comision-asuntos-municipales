# TanStack Query Cache Mutation Patterns

Generic hooks for managing TanStack Query v5 cache mutations with type-safe patterns.

## Overview

These hooks provide building blocks for cache management, from simple updates to full optimistic mutations with rollback.

## Decision Matrix

**Are you creating or adding a new item?**
- **Yes** → `useGenericCreateMutation`
- **No** → Continue below

**Do you need optimistic updates (user sees change immediately)?**
- **Yes** → `useGenericOptimisticUpdate`
- **No** → Continue below

**Do you need bidirectional list/detail sync?**
- **Yes** → `useGenericCacheSync`
- **No** → Continue below

**Are you updating or deleting?**
- **Update** → `useGenericUpdateMutation`
- **Delete** → `useGenericDeleteMutation`

---

## Hooks

### 1. `useGenericCreateMutation`

Adds a new item to both list and detail caches after a successful mutation.

**When to use**: Standard create/add operations where a new item is created and should appear in the cache.

```typescript
import { useGenericCreateMutation } from '@/hooks/cache';

interface Todo {
  id: string;
  title: string;
  completed: boolean;
}

const createTodoMutation = useGenericCreateMutation<Todo>({
  queryKey: ['todos'],
  mutationFn: async (data) => {
    const response = await api.post('/todos/', data);
    return response.data;
  },
  insertPosition: 'start', // 'start' for newest-first, 'end' for oldest-first
});

// In your component:
createTodoMutation.mutate({ title: 'New todo', completed: false });
```

**Cache behavior**:
- Adds new item to list cache at the start or end (based on `insertPosition`)
- Pre-seeds detail cache at `[...queryKey, newItem.id]`

**insertPosition option**:
- `'start'`: Prepends new item — use when list shows newest first (e.g., activity feeds, notifications)
- `'end'`: Appends new item — use when list shows oldest first (e.g., chronological logs)

---

### 2. `useGenericUpdateMutation`

Updates an item in both list and detail caches after a successful mutation.

**When to use**: Standard update operations where the server response should update the cache.

```typescript
import { useGenericUpdateMutation } from '@/hooks/cache';
import { useApiUpdate } from '@/hooks/callsApi';

interface Todo {
  id: string;
  title: string;
  completed: boolean;
}

const updateTodoMutation = useGenericUpdateMutation<Todo>({
  queryKey: ['todos'],
  mutationFn: async ({ id, data }) => {
    // Use your API hook or direct API call
    const response = await api.put(`/todos/${id}/`, data);
    return response.data;
  },
});

// In your component:
updateTodoMutation.mutate({ id: '123', data: { title: 'New title' } });
```

**Cache behavior**:
- Updates item in list cache (matches by `id`)
- Updates detail cache at `[...queryKey, id]`

---

### 3. `useGenericDeleteMutation`

Removes an item from list and detail caches after successful deletion.

**When to use**: Delete operations where the item should disappear from cache.

```typescript
import { useGenericDeleteMutation } from '@/hooks/cache';

interface Todo {
  id: string;
  title: string;
}

const deleteTodoMutation = useGenericDeleteMutation<Todo>({
  queryKey: ['todos'],
  mutationFn: async (id) => {
    await api.delete(`/todos/${id}/`);
  },
});

// In your component:
deleteTodoMutation.mutate('123');
```

**Cache behavior**:
- Filters item out of list cache
- Removes detail cache entry

---

### 4. `useGenericOptimisticUpdate`

Full optimistic update cycle with rollback on error.

**When to use**: When users expect immediate feedback and the operation can be rolled back safely.

```typescript
import { useGenericOptimisticUpdate } from '@/hooks/cache';

interface Todo {
  id: string;
  title: string;
  completed: boolean;
}

const toggleTodoMutation = useGenericOptimisticUpdate<Todo, { id: string; completed: boolean }>({
  queryKey: ['todos'],
  mutationFn: async ({ id, completed }) => {
    const response = await api.patch(`/todos/${id}/`, { completed });
    return response.data;
  },
  updaterFn: (oldData, variables) =>
    oldData?.map((todo) =>
      todo.id === variables.id ? { ...todo, completed: variables.completed } : todo
    ) ?? [],
});

// In your component:
toggleTodoMutation.mutate({ id: '123', completed: true });
```

**Lifecycle**:
1. `onMutate`: Cancel outgoing refetches → Snapshot previous → Optimistic update
2. `onError`: Rollback to snapshot
3. `onSettled`: (Optional) Invalidate queries

---

### 5. `useGenericCacheSync`

Bidirectional sync between list and detail caches. Pre-warms caches and keeps them in sync.

**When to use**: When you have list → detail navigation and want to avoid refetching.

```typescript
import { useGenericCacheSync } from '@/hooks/cache';
import { useQuery } from '@tanstack/react-query';

interface Todo {
  id: string;
  title: string;
  completed: boolean;
}

const { seedDetailCaches, syncItem, removeItem } = useGenericCacheSync<Todo>({
  listQueryKey: ['todos'],
  detailKeyFn: (item) => ['todos', item.id],
});

// Pre-warm caches from list data
const { data: todos } = useQuery({
  queryKey: ['todos'],
  queryFn: fetchTodos,
});

// After list loads, seed detail caches
seedDetailCaches(todos ?? []);

// Sync an updated item to both caches
syncItem({ id: '123', title: 'Updated', completed: false });

// Remove from both caches
removeItem('123');
```

---

## Anti-Patterns

### ❌ Mutating cache directly

```typescript
// ❌ WRONG — mutates oldData
queryClient.setQueryData(['todos'], (old) => {
  old.title = 'new'; // MUTATION!
  return old;
});

// ✅ CORRECT — spread + override
queryClient.setQueryData(['todos'], (old) => 
  old ? { ...old, title: 'new' } : old
);
```

### ❌ Forgetting `cancelQueries`

Without cancellation, an in-flight refetch can overwrite your optimistic update after the user already sees the change.

```typescript
// ❌ WRONG — no cancellation
onMutate: async (variables) => {
  const previousData = queryClient.getQueryData(queryKey);
  queryClient.setQueryData(queryKey, updaterFn(old, variables));
  return { previousData }; // Race condition possible!
};

// ✅ CORRECT — cancel first
onMutate: async (variables) => {
  await queryClient.cancelQueries({ queryKey }); // Stop incoming refetches
  const previousData = queryClient.getQueryData(queryKey);
  queryClient.setQueryData(queryKey, updaterFn(old, variables));
  return { previousData };
};
```

### ❌ Using index as key in lists

When mapping over data for cache updates, ensure stable `id` values:

```typescript
// ✅ CORRECT — use item.id
old?.map((item) => (item.id === updatedItem.id ? updatedItem : item))

// ❌ WRONG — index can cause wrong items to be updated
old?.map((item, index) => (index === targetIndex ? updatedItem : item))
```

---

## Type Requirements

All hooks require items to have a stable `id` field of type `string | number`:

```typescript
interface BaseItem {
  id: string | number;
}
```

If your data uses different id structures, create wrapper hooks with proper typing:

```typescript
function useProjectUpdate() {
  return useGenericUpdateMutation<Project>({
    queryKey: ['projects'],
    mutationFn: async ({ id, data }) => { /* ... */ },
  });
}
```
