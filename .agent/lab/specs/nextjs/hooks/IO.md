# Hooks — TypeScript Signatures

## API Hooks (4)

---

### `useApiQuery<T, TData = T>`

```typescript
interface UseApiQueryProps<T, TData = T> {
  /** React Query cache key — should match entity name */
  queryKey: QueryKey;
  /** API endpoint URL — pass null to disable query */
  url: string | null;
  /** Zod schema for runtime validation of response data */
  schema: ZodType<T>;
  /** Query parameters appended to URL */
  params?: Record<string, unknown>;
  /** Show error toast on failure (default: true) */
  showToast?: boolean;
  /** Additional React Query options (queryKey and queryFn are set by hook) */
  queryOptions?: Omit<UseQueryOptions<T, AxiosError, TData>, "queryKey" | "queryFn">;
}
```

**Returns**: `UseQueryResult<T, AxiosError>` (standard React Query result)

**Generic parameters**:
- `T` — raw response type (validated by Zod schema)
- `TData` — transformed data type (default: same as `T`)

---

### `useApiCreate<TData = unknown, TVariables = unknown>`

```typescript
interface UseApiCreateProps<TData, TVariables> {
  /** API endpoint URL */
  url: string;
  /** Zod schema for response validation (optional) */
  schema?: ZodType<TData>;
  /** Show error toast on failure (default: true) */
  showToast?: boolean;
  /** Additional React Query mutation options */
  options?: Omit<UseMutationOptions<TData, AxiosError, TVariables>, "mutationFn">;
}
```

**Returns**: `UseMutationResult<TData, AxiosError, TVariables>`

**Generic parameters**:
- `TData` — expected response type after schema validation
- `TVariables` — payload type passed to `mutate()`

---

### `useApiUpdate<TData = unknown, TPayload = unknown>`

```typescript
type UpdateVariables<TPayload> = { id: number | string; data: TPayload };

interface UseApiUpdateProps<TData, TPayload> {
  /** Base API URL (hook appends `/{id}/`) */
  baseUrl: string;
  /** Zod schema for response validation (optional) */
  schema?: ZodType<TData>;
  /** HTTP method — PUT or PATCH (default: PUT) */
  method?: "PUT" | "PATCH";
  /** Show error toast on failure (default: true) */
  showToast?: boolean;
  /** Additional React Query mutation options */
  options?: Omit<UseMutationOptions<TData, AxiosError, UpdateVariables<TPayload>>, "mutationFn">;
}
```

**Returns**: `UseMutationResult<TData, AxiosError, UpdateVariables<TPayload>>`

**Generic parameters**:
- `TData` — expected response type
- `TPayload` — the data payload type being sent in the update request

---

### `useApiDelete<TData = unknown>`

```typescript
interface UseApiDeleteProps<TData> {
  /** Base API URL (hook appends `/{id}/`) */
  baseUrl: string;
  /** Show error toast on failure (default: true) */
  showToast?: boolean;
  /** Additional React Query mutation options */
  options?: Omit<UseMutationOptions<TData, AxiosError, number | string>, "mutationFn">;
}
```

**Returns**: `UseMutationResult<TData, AxiosError, number | string>`

**Generic parameters**:
- `TData` — expected response type after deletion

**Note**: Mutation variable is the ID to delete (`number` or `string`), not an object.

---

## System Hooks (3)

---

### `useDebounce<T>`

```typescript
function useDebounce<T>(value: T, delay: number): T
```

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `value` | `T` | The value to debounce |
| `delay` | `number` | Delay in milliseconds |

**Returns**: `T` — the debounced value (updated after `delay` ms of inactivity)

**Generic parameters**:
- `T` — any type — the debounced value preserves the original type

---

### `usePagination`

```typescript
interface UsePaginationProps {
  /** Initial page number (default: 1) */
  initialPage?: number;
  /** Initial page size (default: 10) */
  initialPageSize?: number;
}

interface UsePaginationReturn {
  /** Current page number */
  page: number;
  /** Current page size */
  pageSize: number;
  /** Callback to change to a specific page */
  onPageChange: (newPage: number) => void;
  /** Callback to change page size (resets to page 1) */
  onPageSizeChange: (newPageSize: number) => void;
  /** Params object to spread into useApiQuery.params */
  paginationParams: { page: number; page_size: number };
}
```

**Returns**: `UsePaginationReturn`

---

### `useIsMobile`

```typescript
function useIsMobile(): boolean
```

**Returns**: `boolean` — `true` if viewport width < 768px, `false` otherwise

**Note**: Returns `undefined` during initial render before effect runs, then `boolean`.

---

## Imported Types Reference

| Type | Source | Used By |
|------|--------|---------|
| `QueryKey` | `@tanstack/react-query` | `useApiQuery` |
| `UseQueryOptions` | `@tanstack/react-query` | `useApiQuery` |
| `UseMutationOptions` | `@tanstack/react-query` | `useApiCreate`, `useApiUpdate`, `useApiDelete` |
| `AxiosError` | `axios` | All API hooks |
| `ZodType<T>` | `zod` | API hooks with schema prop |
| `UseQueryResult`, `UseMutationResult` | `@tanstack/react-query` | Return types |
