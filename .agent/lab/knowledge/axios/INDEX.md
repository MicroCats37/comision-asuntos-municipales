# Axios Knowledge Index

## Documents
| Doc | Topic | When to Read |
|-----|-------|-------------|
| [instance-config.md](./instance-config.md) | Instance Setup | Initial API configuration |
| [interceptors.md](./interceptors.md) | Interceptors | Auth tokens & Error logging |
| [error-handling.md](./error-handling.md) | Errors | Global error patterns |
| [cancellation.md](./cancellation.md) | Cancellation | AbortController integration |

## Quick Reference
- Standard path: `src/lib/api.ts`
- Always use Zod for runtime validation of API responses.
- Integration: Pair with TanStack Query for caching.
