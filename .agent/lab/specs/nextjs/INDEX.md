# Next.js Architecture Specs Index

## Core Specifications
| Spec | Focus | Status | Files |
|------|-------|--------|-------|
| [Project Structure](./project-structure/SPEC.md) | Folder arch, imports, naming, barrels | ✅ Done | [Spec](./project-structure/SPEC.md) · [IO](./project-structure/IO.md) · [Examples](./project-structure/EXAMPLES.md) |
| [Forms](./forms/SPEC.md) | GenericForm modes, payload strategy, schema structure | ✅ Done | [Spec](./forms/SPEC.md) · [IO](./forms/IO.md) · [Examples](./forms/EXAMPLES.md) |
| [Modals](./modals/SPEC.md) | Compound Components, dynamic width, Context injection | ✅ Done | [Spec](./modals/SPEC.md) · [IO](./modals/IO.md) · [Examples](./modals/EXAMPLES.md) |
| [Hooks](./hooks/SPEC.md) | React Query API hooks, system utilities (debounce, pagination, mobile detection) | ✅ Done | [Spec](./hooks/SPEC.md) · [IO](./hooks/IO.md) · [Examples](./hooks/EXAMPLES.md) |
| [Date Formatter](./date-formatter/SPEC.md) | date-fns v4 utility with Spanish locale, 4 formatting functions | ✅ Done | [Spec](./date-formatter/SPEC.md) · [IO](./date-formatter/IO.md) · [Examples](./date-formatter/EXAMPLES.md) |
| [DataTable](./data-table/SPEC.md) | GenericDataTable modes, column helpers, pagination, URL state sync | ✅ Done | [Spec](./data-table/SPEC.md) · [IO](./data-table/IO.md) · [Examples](./data-table/EXAMPLES.md) |
| [Error Boundary](./error-boundary/SPEC.md) | GenericErrorBoundary class component, fallback render prop, notify.error() | ✅ Done | [Spec](./error-boundary/SPEC.md) · [IO](./error-boundary/IO.md) · [Examples](./error-boundary/EXAMPLES.md) |
| [Empty State](./empty-state/SPEC.md) | EmptyState component for tables, lists, cards | ✅ Done | [Spec](./empty-state/SPEC.md) · [IO](./empty-state/IO.md) · [Examples](./empty-state/EXAMPLES.md) |
| [Confirmation Dialog](./confirmation-dialog/SPEC.md) | ConfirmationDialog + useConfirmationDialog hook for destructive confirmations | ✅ Done | [Spec](./confirmation-dialog/SPEC.md) · [IO](./confirmation-dialog/IO.md) · [Examples](./confirmation-dialog/EXAMPLES.md) |
| [Breadcrumbs](./breadcrumbs/SPEC.md) | Manual items array, current page = no href, icon support | ✅ Done | [Spec](./breadcrumbs/SPEC.md) · [IO](./breadcrumbs/IO.md) · [Examples](./breadcrumbs/EXAMPLES.md) |
| [Tabs](./tabs/SPEC.md) | GenericTabs with local/URL state, Suspense wrapper for syncUrl | ✅ Done | [Spec](./tabs/SPEC.md) · [IO](./tabs/IO.md) · [Examples](./tabs/EXAMPLES.md) |
| [Data Flow](./data-flow/SPEC.md) | Server vs Client fetching | Pending | — |
| [Auth](./auth/SPEC.md) | Protected routes + Session | Pending | — |

## Cross-Cutting Contracts
Shared contracts that apply to all specs:

| Contract | Scope | Files |
|----------|-------|-------|
| [Error Handling](./shared/error-handling.md) | Parser chain, toast adapter | [Contract](./shared/error-handling.md) |
| [API Format](./shared/api-format.md) | Response shapes, payload builders | [Contract](./shared/api-format.md) |
| [Type Conventions](./shared/types.md) | Schema naming, inference patterns | [Contract](./shared/types.md) |
| [Env Conventions](./shared/env-conventions.md) | Env vars, test flags | [Contract](./shared/env-conventions.md) |

## Spec File Structure (3-File Pattern)

Each spec contains exactly three files:

| File | Purpose |
|------|---------|
| `SPEC.md` | Rules, REQUIRED/FORBIDDEN patterns, architectural decisions |
| `IO.md` | Component props, data contracts, type signatures |
| `EXAMPLES.md` | Runnable code examples for each documented pattern |

## Governance
- All specs follow the **React 19 + Next.js 16** standard.
- Specs are source-of-truth for the AI.
- Refer to `../../knowledge/` for fundamental concepts.
- Each spec MUST have `❌ FORBIDDEN` and `✅ REQUIRED` sections.
