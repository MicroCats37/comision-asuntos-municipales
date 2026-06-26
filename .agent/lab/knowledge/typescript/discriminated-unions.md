# TypeScript: Discriminated Unions

## What is it
A pattern in TypeScript for creating a type that can be one of several different shapes, differentiated by a common "discriminant" property.

## Golden Rules
- ✅ DO: Use a string literal field (like `type` or `status`) as the discriminant.
- ✅ DO: Use an `exhaustive check` (e.g., using `never`) to ensure all cases are handled in a switch statement.
- ❌ DON'T: Use multiple optional boolean flags (`isLoading`, `isError`) for state management; use a union instead.

## Canonical Code

```typescript
type UIState = 
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: string[] }
  | { status: 'error'; message: string };

function renderUI(state: UIState) {
  switch (state.status) {
    case 'idle': return 'Waiting...';
    case 'loading': return 'Cargando...';
    case 'success': return state.data.map(i => i);
    case 'error': return state.message;
    default: {
      const _exhaustiveCheck: never = state;
      return _exhaustiveCheck;
    }
  }
}
```

## Gotchas
- Discriminated unions only work if the differentiation property is primitive (string, number, boolean) and literal.