# Zod Knowledge Index

## Documents
| Doc | Topic | When to Read |
|-----|-------|-------------|
| [inference.md](./inference.md) | Inference | z.infer & types |
| [refinements.md](./refinements.md) | Refinements | Custom validation logic |
| [transformations.md](./transformations.md) | Transforms | Data normalization |
| [composition.md](./composition.md) | Composition | Merging & Extending schemas |
| [forms-integration.md](./forms-integration.md) | Forms | RHF integration |

## Quick Reference
- Use `z.infer<typeof schema>` as source of truth for types.
- Never write manual TypeScript interfaces for validated objects.
- Integration: Use with RHF via `@hookform/resolvers/zod`.
