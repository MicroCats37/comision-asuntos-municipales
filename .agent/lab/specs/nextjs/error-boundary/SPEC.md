# Error Boundary Spec

## Metadata
- Version: 1.0
- Stack: Next.js 16 + React 19 + TypeScript
- Scope: GenericErrorBoundary error catching, fallback rendering, error notification

---

## Core Principle

> **Wrap any component tree that may throw with `GenericErrorBoundary`. Errors must never pass silently.**

`GenericErrorBoundary` is a class component that catches JavaScript errors in child component trees and displays a fallback UI. It also notifies the error tracking system via `notify.error()`.

---

## Rules

### ✅ REQUIRED

- Must be a **class component** — function components cannot implement `componentDidCatch`
- Accept a `fallback` render prop for custom error UI
- Call `notify.error()` in `componentDidCatch` to log errors externally
- Use the fallback render prop pattern when you need access to the error object and reset handler

### ❌ FORBIDDEN

- Using `useState` for error state in a function component — React's error boundary must be a class
- Swallowing errors silently without calling `notify.error()` or `onError`
- Nesting error boundaries too deeply (catches at logical app boundaries, not every leaf component)

---

## Behavior

### Error Catching

When an error is thrown inside the component tree:

1. `getDerivedStateFromError` sets `hasError: true` and stores the error
2. `componentDidCatch` calls `notify.error()` if available in browser context
3. `onError` prop callback is invoked with error and error info
4. `render()` displays the fallback UI or default error message

### Reset

The `handleReset` method clears error state. If a custom fallback is provided, it receives the reset function as an argument.

---

## Source References

→ [`references/SOURCES.md`](./references/SOURCES.md)