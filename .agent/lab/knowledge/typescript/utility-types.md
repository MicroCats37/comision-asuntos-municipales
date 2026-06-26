# TypeScript: Utility Types

## What is it
Built-in types provided by TypeScript to transform and manipulate existing types (e.g., `Pick`, `Omit`, `Partial`).

## Golden Rules
- ✅ DO: Use `Pick<User, 'id' | 'name'>` to create a subset of an interface for a specific component.
- ✅ DO: Use `ReturnType<typeof function>` to link types to implementation logic.
- ❌ DON'T: Nest utility types excessively; it makes the types hard to read and debug.

## Canonical Code

```typescript
interface User {
  id: string;
  name: string;
  email: string;
}

// Creation of a partial update type
type UserUpdate = Partial<Omit<User, 'id'>>;

// Using ReturnType
const getUser = () => ({ id: '1', name: 'John' });
type UserResult = ReturnType<typeof getUser>;
```

## Gotchas
- `Required<T>` can break things if underlying properties are optional for a reason; use it sparingly.