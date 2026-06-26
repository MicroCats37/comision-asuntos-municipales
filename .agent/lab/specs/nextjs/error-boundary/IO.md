# Error Boundary: Inputs & Outputs

## Component API

### GenericErrorBoundary Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `children` | `ReactNode` | Yes | — | Child components to wrap |
| `fallback` | `(error: Error, reset: () => void) => ReactNode` | No | Default error UI | Custom fallback renderer |
| `onError` | `(error: Error, errorInfo: ErrorInfo) => void` | No | — | Callback when error is caught |

### ErrorBoundaryState

```typescript
interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}
```

### ErrorInfo

```typescript
interface ErrorInfo {
  componentStack?: string
  // Inherited from React.ErrorInfo
}
```

## Default Fallback

When no `fallback` prop is provided, renders:

```tsx
<div className="p-4 text-center">
  <p className="text-destructive">Something went wrong</p>
  <button type="button" onClick={reset} className="mt-2 underline">
    Try again
  </button>
</div>
```

## Error Notification Contract

Errors are logged via the `notify` adapter from `@/errors`:

```typescript
import('@/errors').then(({ notify }) => {
  notify.error(error.message || 'An error occurred')
})
```

This ensures all errors flow through the application's error handling infrastructure.

## See Also
- [Spec: Error Boundary](./SPEC.md) — full spec
- [Shared: Error Handling](../shared/error-handling.md) — error contract