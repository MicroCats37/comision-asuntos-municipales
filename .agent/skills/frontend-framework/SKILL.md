---
name: frontend-framework
description: "Trigger: frontend, nextjs, react, hooks, cache, UI. Enforce the custom Next.js architecture, generic components, and explicit cache hooks."
license: Apache-2.0
metadata:
  author: "gentleman-programming"
  version: "1.0"
---

## Activation Contract

Create or modify frontend features in the Next.js application.
The architecture acts as an internal framework; you must use its provided abstractions (Generic Components, Generic Hooks, Cache Hooks) rather than building from scratch or using raw libraries directly.

## Hard Rules

- **Internal Framework**: The architecture is an internal framework. NEVER reinvent the wheel.
- **Strict Generic Components**: You MUST use the provided generic components (`app components` like `GenericForm`, `GenericDataTable`, `GenericModal`) for application-specific UI.
- **Strict Generic Hooks**: All business logic and data fetching MUST use the provided generic hooks (e.g., `useApiQuery`, `useApiCreate`).
- **Cache Hooks (CRITICAL)**: You MUST explicitly use custom Cache Hooks for state and data management. This pattern is central to this stack.
- **Folder Structure**: `app/` is for routing ONLY. All business logic lives in `src/features/{domain}/`.
- **Server/Client Boundary**: Server Components by default. Use `'use client'` only when interactivity is required, placed as low as possible.
- **Naming Conventions**: Use `{Action}{Resource}FormSchema` and `{Action}{Resource}Data`. Prefix hooks with `use`.
- **Imports**: No wildcard re-exports. No default imports for React. Use named imports.
- **Forms**: Use `GenericForm` in Mode 1 (manual `children` render prop) for production screens. Mode 2 and 3 are FORBIDDEN in production.
- **Tables**: Use `GenericDataTable` with `mode="url"` for full-page tables.
- **Error Handling**: Use `handleApiError` from `@/errors/error-handler` and `notify` from `@/errors/toast-adapter`. NEVER call `toast()` directly.
- **Modals**: Use the Compound Components pattern for Modals (e.g., `<GenericModal>`, `<GenericModal.Trigger>`).

## Decision Gates

| Need | Action |
|------|--------|
| Need a form for production | Use `GenericForm` with Mode 1 (children render prop) |
| Need a full-page data table | Use `GenericDataTable` with `mode="url"` |
| Need a modal | Use `GenericModal` compound components (`Trigger`, `Content`, `Header`, etc.) |
| Need to fetch or mutate data | Use Generic Hooks and strictly integrate custom **Cache Hooks** |
| Need to handle API errors | Use `handleApiError` and `notify` adapter |

## Execution Steps

1. Analyze the feature domain and locate it under `src/features/{domain}/`.
2. Define Zod schemas using `{Action}{Resource}FormSchema`.
3. Build the UI exclusively by composing the internal framework's Generic Components.
4. Implement business logic and data fetching using the strict Generic Hooks.
5. Explicitly apply the custom Cache Hooks to manage caching and data states.
6. Assemble the route in `app/` referencing the feature components, ensuring no business logic leaks into the route file.
7. Verify all imports use named imports and strict alias patterns.

## Output Contract

Return:
- The updated or created files adhering to the architecture.
- A brief explanation of which generic components and cache hooks were utilized.

## References

- `src/features/` - Domain business logic
- `components/ui/` - Generic reusable UI (Shadcn)