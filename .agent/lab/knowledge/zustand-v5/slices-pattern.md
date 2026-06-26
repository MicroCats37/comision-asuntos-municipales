# Zustand v5: Slice Pattern (Modularity)

## What is it
A strategy for dividing a giant global store into smaller files (slices), while maintaining TypeScript typing and a single unified store.

## Golden Rules
- ✅ DO: Create one file per logic domain (e.g., `authSlice.ts`, `cartSlice.ts`).
- ✅ DO: Use the `StateCreator<T>` type to define each slice with total type safety.
- ❌ DON'T: Create multiple independent stores unless data has absolutely no relationship across domains.

## Canonical Code

```typescript
import { create, StateCreator } from 'zustand';

// 1. User Slice Definition
interface UserSlice {
  user: string | null;
  setUser: (user: string) => void;
}

const createUserSlice: StateCreator<UserSlice> = (set) => ({
  user: null,
  setUser: (user) => set({ user }),
});

// 2. UI Slice Definition
interface UISlice {
  theme: 'light' | 'dark';
  toggleTheme: () => void;
}

const createUISlice: StateCreator<UISlice> = (set) => ({
  theme: 'light',
  toggleTheme: () => set((state) => ({ 
    theme: state.theme === 'light' ? 'dark' : 'light' 
  })),
});

// 3. Union in the Main Store
export const useBoundStore = create<UserSlice & UISlice>()((...a) => ({
  ...createUserSlice(...a),
  ...createUISlice(...a),
}));
```

## Gotchas
- The order of functions in `create` matters if slices depend on each other.
- Middleware like `persist` should wrap the principal function merging all slices.