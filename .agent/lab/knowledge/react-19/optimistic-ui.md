# React 19: useOptimistic

## What is it
A hook that allows showing an immediate "success" state in the UI while an asynchronous operation (like a Server Action) is happening in the background. If the operation fails, React automatically reverts to the real state.

## Golden Rules
- ✅ DO: Use for frequent, low-latency perceived actions (Likes, add to cart, name changes).
- ✅ DO: Ensure the optimistic state is visually indistinguishable from the final state for a seamless experience.
- ❌ DON'T: Use for critical operations where failure is common or catastrophic (e.g., deleting an account).

## Canonical Code

```jsx
import { useOptimistic } from 'react';

function Cart({ initialCount, updateAction }) {
  const [optimisticCount, setOptimisticCount] = useOptimistic(
    initialCount,
    (state, newCount) => newCount // Optimistic update logic
  );

  async function handleAdd() {
    setOptimisticCount(initialCount + 1); // UI updates instantly
    await updateAction(initialCount + 1); // Server confirms later
  }

  return (
    <div>
      <span>Tickets: {optimisticCount}</span>
      <button onClick={handleAdd}>+</button>
    </div>
  );
}
```

## Gotchas
- The optimistic state is "discarded" as soon as the component re-renders with real server data.
- You must handle the logic of merging old and new states in the reducer function (second argument).