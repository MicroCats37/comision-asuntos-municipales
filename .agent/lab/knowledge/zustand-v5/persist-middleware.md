# Zustand v5: Persist Middleware

## What is it
Middleware that automatically saves the store's state in persistent storage (`localStorage`, `sessionStorage`, or IndexedDB) and retrieves it on page reload.

## Golden Rules
- ✅ DO: Always give a unique `name` to each persistent store.
- ✅ DO: Use `createJSONStorage` to specify where to save the data (defaults to `localStorage`).
- ❌ DON'T: Save sensitive data (passwords, critical tokens) in unencrypted persistent storage.

## Canonical Code

```typescript
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface AuthStore {
  token: string | null;
  setToken: (token: string) => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      token: null,
      setToken: (token) => set({ token }),
    }),
    {
      name: 'auth-storage', // localStorage key
      storage: createJSONStorage(() => localStorage),
    }
  )
);
```

## Gotchas
- If you change the store's structure, users might have "old" data in their browser. Use the `version` property and the `migrate` function in the middleware if needed.
- Hydration is async by default. Use `onRehydrateStorage` to know when it finishes.