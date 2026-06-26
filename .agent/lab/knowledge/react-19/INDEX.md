# React 19 Knowledge Index

## Documents
| Doc | Topic | When to Read |
|-----|-------|-------------|
| [action-hooks.md](./action-hooks.md) | Action Hooks | useActionState & useFormStatus |
| [optimistic-ui.md](./optimistic-ui.md) | Optimistic UI | useOptimistic pattern |
| [use-hook.md](./use-hook.md) | use() Hook | Consuming Promises/Context |
| [refs-simplified.md](./refs-simplified.md) | Refs | Prop-based refs (no forwardRef) |
| [compiler-era.md](./compiler-era.md) | Compiler | Memoization & Performance |
| [breaking-changes.md](./breaking-changes.md) | Migration | Deprecated features |

## Quick Reference
- Forget `forwardRef`, use `ref` as prop.
- Forget manually memoizing everything (Compiler handles it).
- Use `useActionState` for all async form actions.
