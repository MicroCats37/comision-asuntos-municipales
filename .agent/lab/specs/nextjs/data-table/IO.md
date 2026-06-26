# DataTable: Inputs & Outputs

## Component API

### GenericDataTable Props

```typescript
interface DataTableProps<T extends Record<string, unknown>> {
  /** Column definitions created via createColumns<T>() */
  columns: ColumnDef<T>[];
  /** Pre-filtered data array — NEVER fetch inside the table */
  data: T[];
  /** Loading state from useApiQuery */
  isLoading?: boolean;
  /** Table mode: 'url' for full-page, 'local' for embedded */
  mode?: 'url' | 'local';
  /** Pagination state — controlled externally */
  pagination?: PaginationState;
  /** Callback when pagination changes */
  onPaginationChange?: (pagination: PaginationState) => void;
  /** Callback when sorting changes */
  onSortingChange?: (sorting: SortingParam | null) => void;
  /** Empty state component */
  emptyState?: ReactNode;
  /** Additional CSS classes */
  className?: string;
}
```

### PaginationState

```typescript
interface PaginationState {
  page: number;       // Current page (1-indexed)
  pageSize: number;   // Items per page
  totalPages: number; // Total number of pages
  totalItems: number; // Total number of items
}
```

### SortingParam

```typescript
interface SortingParam {
  field: string;           // Field name to sort by
  direction: 'asc' | 'desc'; // Sort direction
}
```

### TableMode

```typescript
type TableMode = 'url' | 'local';
```

---

## Column Helper Signatures

### createColumns

```typescript
function createColumns<T>(columns: ColumnDef<T>[]): ColumnDef<T>[]
```

### textColumn

```typescript
function textColumn(
  key: string,                    // Data field key
  label: string,                   // Column header label
  options?: {
    sortable?: boolean;            // Enable sorting (default: false)
    className?: string;            // Additional cell classes
  }
): ColumnDef<T>
```

### dateColumn

```typescript
function dateColumn(
  key: string,                    // Data field key (Date or ISO string)
  label: string,                   // Column header label
  options?: {
    format?: 'short' | 'long' | 'relative';  // Format preset (default: 'short')
    sortable?: boolean;            // Enable sorting (default: false)
    className?: string;           // Additional cell classes
  }
): ColumnDef<T>
```

### numberColumn

```typescript
function numberColumn(
  key: string,                    // Data field key
  label: string,                   // Column header label
  options?: {
    format?: (value: number) => string;  // Custom formatter function
    sortable?: boolean;            // Enable sorting (default: false)
    className?: string;           // Additional cell classes
  }
): ColumnDef<T>
```

### badgeColumn

```typescript
function badgeColumn(
  key: string,                    // Data field key (string value)
  label: string,                   // Column header label
  badgeClassMap: Record<string, string>  // Value → CSS class mapping
): ColumnDef<T>
```

### actionsColumn

```typescript
function actionsColumn(
  actions: Array<{
    label: string;
    onClick: (row: T) => void;
    variant?: 'default' | 'destructive';
  }>
): ColumnDef<T>
```

---

## Data Contracts

### Table State Flow

```
usePagination() / useState
         ↓
   pagination state
         ↓
GenericDataTable ← data from useApiQuery
         ↓
onPaginationChange → updates parent state
onSortingChange → updates ordering param → triggers refetch
```

### URL Param Contract (mode="url")

| URL Param | Internal State | Example |
|-----------|----------------|---------|
| `page` | `pagination.page` | `?page=2` |
| `pageSize` | `pagination.pageSize` | `?pageSize=20` |
| `sort` | `SortingParam` | `?sort=-created_at` (descending) |

---

## Server Action Signatures

### useApiQuery (for table data)

```typescript
function useApiQuery<TData>({
  queryKey: [string, Record<string, unknown>];
  url: string;
  params?: Record<string, unknown>;
  schema: ZodSchema<TData>;
}): {
  data: TData | undefined;
  isLoading: boolean;
}
```

### usePagination hook

```typescript
function usePagination(defaultPageSize?: number): {
  page: number;
  pageSize: number;
  onPageChange: (newPage: number) => void;
  onPageSizeChange: (newSize: number) => void;
}
```

---

## Error Handling

GenericDataTable handles **zero** error logic internally.
Errors from `useApiQuery` are handled by the feature component via `handleApiError`.

Feature components should:
1. Pass `isLoading` to GenericDataTable during data fetching
2. Handle errors via `handleApiError` in the query configuration
3. Show appropriate `emptyState` when data is empty

---

## See Also
- [Spec: DataTable](./SPEC.md) — full spec
- [Spec: Hooks](./hooks/SPEC.md) — usePagination, useApiQuery
- [Spec: Date Formatter](./date-formatter/SPEC.md) — date-fns utility
