# Error Boundary: Worked Examples

## Example 1: Basic Usage

Wrapping a component tree with the default fallback:

```tsx
import { GenericErrorBoundary } from "@/components/genericErrorBoundary/GenericErrorBoundary";
import { Suspense } from "react";
import { ProductList } from "./ProductList";

export function ProductsPage() {
  return (
    <GenericErrorBoundary>
      <Suspense fallback={<div>Loading...</div>}>
        <ProductList />
      </Suspense>
    </GenericErrorBoundary>
  );
}
```

## Example 2: Custom Fallback

Providing a render prop for custom error UI:

```tsx
import { GenericErrorBoundary } from "@/components/genericErrorBoundary/GenericErrorBoundary";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";

export function DataWidget() {
  return (
    <GenericErrorBoundary
      fallback={(error, reset) => (
        <div className="flex flex-col items-center p-6 border rounded-lg border-destructive/50 bg-destructive/10">
          <AlertTriangle className="h-8 w-8 text-destructive mb-2" />
          <h3 className="font-semibold">Widget Error</h3>
          <p className="text-sm text-muted-foreground mb-4">{error.message}</p>
          <Button variant="outline" onClick={reset}>
            Retry
          </Button>
        </div>
      )}
    >
      <WeatherWidget />
    </GenericErrorBoundary>
  );
}
```

## Example 3: With onError Callback

Tracking errors to an external service:

```tsx
import { GenericErrorBoundary } from "@/components/genericErrorBoundary/GenericErrorBoundary";
import { logError } from "@/analytics";

export function Dashboard() {
  return (
    <GenericErrorBoundary
      onError={(error, errorInfo) => {
        logError("DashboardError", error, errorInfo);
      }}
    >
      <DashboardContent />
    </GenericErrorBoundary>
  );
}
```

## Example 4: Wrapping TanStack Query Consumer

Protecting query-dependent UI from render errors:

```tsx
import { GenericErrorBoundary } from "@/components/genericErrorBoundary/GenericErrorBoundary";
import { useUserList } from "@/features/users/hooks";

export function UserSection() {
  const { data: users } = useUserList();

  return (
    <GenericErrorBoundary
      fallback={(error, reset) => (
        <div className="p-4 text-center">
          <p>Failed to load users</p>
          <button onClick={reset}>Try again</button>
        </div>
      )}
    >
      <UserList users={users} />
    </GenericErrorBoundary>
  );
}
```

## See Also
- [Spec: Error Boundary](./SPEC.md) — full spec
- [Shared: Error Handling](../shared/error-handling.md) — error contract