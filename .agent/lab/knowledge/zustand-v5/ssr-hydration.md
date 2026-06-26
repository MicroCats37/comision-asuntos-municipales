# Zustand v5: SSR & Hydration (Next.js)

## What is it
The technical solution to avoid "Hydration Mismatch" errors in Next.js, caused by the server rendering an initial state while the client has another (e.g., from LocalStorage).

## Golden Rules
- ✅ DO: Use the custom `useStore` hook to delay state access until the component mounts in the client.
- ✅ DO: Ensure the initial server state matches the store's default values.
- ❌ DON'T: Directly access the store in the component body if the store uses persistence.

## Canonical Code (The Gold Hook)

```typescript
// hooks/useStore.ts
import { useState, useEffect } from 'react';

export const useStore = <T, F>(
  store: (callback: (state: T) => unknown) => unknown,
  callback: (state: T) => F
) => {
  const result = store(callback) as F;
  const [data, setData] = useState<F>();

  useEffect(() => {
    setData(result);
  }, [result]);

  return data;
};

// Component usage:
// const count = useStore(useBearStore, (s) => s.bears);
```

## Gotchas
- During first render on the server, `data` is `undefined`. Handle this case in your UI (e.g., show a skeleton).
- Don't use this hook for non-persisted states, as it adds an unnecessary render cycle.