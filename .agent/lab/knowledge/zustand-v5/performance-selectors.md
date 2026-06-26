# Zustand v5: Performance & Selectors

## What is it
Techniques to ensure your components only re-render when the specific part of the state they use changes.

## Golden Rules
- ✅ DO: Use atomic selectors whenever possible.
- ✅ DO: Use `useShallow` when you need to extract multiple properties in a single object.
- ❌ DON'T: Extract the entire state (`const state = useStore()`) if you only need one property.

## Canonical Code

```typescript
import { useStore } from './store';
import { useShallow } from 'zustand/react/shallow';

// 1. Atomic Selector (Recommended)
function UserDisplay() {
  const name = useStore((state) => state.username);
  return <div>{name}</div>;
}

// 2. Multiple properties with useShallow
function Navbar() {
  const { user, logout } = useStore(
    useShallow((state) => ({ user: state.user, logout: state.logout }))
  );
  return <nav>{/* ... */}</nav>;
}
```

## Gotchas
- Without `useShallow`, extracting a literal object `() => ({ a, b })` will cause re-renders on **EVERY** store change because the object is always a new reference.
- Zustand v5 improved inference, but selectors remain best practice for self-documenting code.