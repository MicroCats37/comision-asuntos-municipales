# Zustand v5 Knowledge Index

## Documents
| Doc | Topic | When to Read |
|-----|-------|-------------|
| [slices-pattern.md](./slices-pattern.md) | Slices | Store modularity |
| [ssr-hydration.md](./ssr-hydration.md) | SSR Hydration | Next.js mismatch fixes |
| [persist-middleware.md](./persist-middleware.md) | Persistence | localStorage integration |
| [performance-selectors.md](./performance-selectors.md) | Performance | Atomic selectors & useShallow |

## Quick Reference
- Use Slice pattern for complex apps.
- Always use `useShallow` when selecting multiple properties.
- Use custom `useStore` hook for SSR safety.
