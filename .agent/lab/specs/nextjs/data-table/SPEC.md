# GenericDataTable Spec

## Metadata
- Version: 1.0
- Stack: Next.js 16 + React 19 + TypeScript + TanStack Table v8
- Scope: GenericDataTable rendering modes, column definitions, pagination, sorting

---

## Core Principle

> **`GenericDataTable` owns rendering and state sync. Features own data fetching and external filters.**

`GenericDataTable` is a headless table controller. Its job is column rendering, pagination UI, and URL/memory state synchronization.
It does **not** own: data fetching, filter logic, or data transformation.

---

## The 2 Rendering Modes

### Mode 1 — URL (`mode="url"`) ✅ REQUIRED for all full-page tables

Table state (page, pageSize, sorting) is synced to the URL query params.
Supports shareable URLs and browser back/forward navigation.

**When to use:** Every page that displays a standalone table with its own URL.

**Required:** Wrap parent in `<Suspense>` when using mode="url".

### Mode 2 — Local (`mode="local"`)

Table state is held in component memory. No URL sync.

**When to use:** Embedded tables inside cards, modals, or sidebars.

---

## Column Definitions

Always use `createColumns<T>()` helper with typed column helpers:

| Helper | Use When |
|--------|----------|
| `textColumn(key, label, opts)` | Plain text values |
| `dateColumn(key, label, opts)` | Date values — uses dateColumn, never format inline |
| `numberColumn(key, label, opts)` | Numeric values with optional formatting |
| `badgeColumn(key, label, badgeClassMap)` | Status badges with CSS class mapping |
| `actionsColumn(actions)` | Row action buttons |

---

## Decision Matrix

| Scenario | Mode |
|---|---|
| Full-page table with its own URL | mode="url" ✅ |
| Table embedded in a card/modal | mode="local" |
| Need shareable URL with filters | mode="url" + external filters ✅ |
| Quick admin table with no URL | mode="local" |

---

## Pagination Strategy

> **`GenericPagination` lives inside `GenericDataTable`. Pagination state is controlled externally via `onPaginationChange`.**

Features pass `pagination` prop with `{ page, pageSize, totalPages, totalItems }`.
Sorting is passed separately via `onSortingChange`.

```
Feature Component → usePagination() → pagination state → GenericDataTable
```

---

## URL State Contract (mode="url")

For mode="url", the component reads from and writes to URL search params:

| Param | Type | Description |
|-------|------|-------------|
| `page` | number | Current page (1-indexed) |
| `pageSize` | number | Items per page |
| `sort` | string | Sorting field and direction (e.g., `-created_at`) |

---

## ✅ REQUIRED

- Always define columns with `createColumns<T>()` helpers
- Always pass pre-filtered data — filters live OUTSIDE the component
- Use `mode="url"` for full-page tables (supports shareable URLs)
- Use `mode="local"` for embedded tables (inside cards, modals)
- Wrap parent in `<Suspense>` when using `mode="url"`
- Use `dateColumn()` — never format dates inline inside column renders
- Use `GenericPagination` for consistent pagination UX
- Sort param format: `-field` for descending, `field` for ascending

---

## ❌ FORBIDDEN

| Pattern | Why |
|---|---|
| Internal filter logic inside GenericDataTable | Filters must be reusable outside table |
| Fetching data inside GenericDataTable | Always receive from `useApiQuery` |
| Hardcoded column definitions outside `createColumns` helpers | Breaks type inference |
| `new Date().toLocaleDateString()` in column renders | Use `dateColumn` with date-fns |
| Fixed `grid-cols-N` for table containers | Use responsive layout |
| Inline sorting logic inside table | Use `onSortingChange` callback |

---

## Decision Log

| Decision | Rationale |
|----------|-----------|
| Filters are external | Decouples filtering from rendering — filters can be reused elsewhere |
| mode="url" as default for pages | Shareable URLs, browser back button works |
| `createColumns<T>()` | Type inference flows from column definition — no type casting needed |
| Uses GenericPagination | Consistent pagination UX across all tables |
| dateColumn() helper | Ensures consistent date formatting with date-fns |

---

## Source References

→ [`references/SOURCES.md`](./references/SOURCES.md)
