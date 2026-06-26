# Hooks Specification

## Overview

Standardized React Query hooks for API communication and system utilities for debouncing, pagination, and mobile detection.

---

## API Hooks (4)

### `useApiQuery`

**Purpose**: Fetches data from the API with automatic Zod schema validation and error toast notifications.

```typescript
const { data, isLoading, error } = useApiQuery<User[]>({
  queryKey: ["users"],
  url: "/users/",
  schema: UserSchema,
  params: { page: 1, page_size: 10 },
});
```

#### ✅ REQUIRED
- Always pass a `schema` prop for runtime validation — never skip it
- Use a `queryKey` that matches the entity name (e.g., `["users"]`, `["products", productId]`)
- The `url` prop accepts `null` to conditionally disable the query
- Spread `paginationParams` from `usePagination` directly into `params`

#### ❌ FORBIDDEN
- Calling `api.get()` directly in components — always go through the hook
- Skipping the Zod schema — without it, runtime validation is bypassed
- Mutating `queryKey` array after creation — React Query uses it for cache identity

---

### `useApiCreate`

**Purpose**: Creates a new resource via POST request, automatically handling payload building and error notifications.

```typescript
const createUser = useApiCreate<User, CreateUserPayload>({
  url: "/users/",
  schema: UserSchema,
});

createUser.mutate({ name: "Ana", email: "ana@example.com" });
```

#### ✅ REQUIRED
- Use `buildApiPayload` via the hook — never call it directly from components
- The hook auto-detects `File`/`Blob` fields and builds `FormData` when needed
- Provide a `schema` for response validation when available

#### ❌ FORBIDDEN
- Calling `buildApiPayload` directly in component code — the hook handles this
- Wrapping the mutation in manual `try/catch` — the hook emits toast errors automatically
- Calling `api.post` directly — bypasses error handling and validation

---

### `useApiUpdate`

**Purpose**: Updates an existing resource via PUT or PATCH request using the `baseUrl` + `id` pattern.

```typescript
const updateUser = useApiUpdate<User, UpdateUserPayload>({
  baseUrl: "/users/",
  schema: UserSchema,
  method: "PUT",
});

updateUser.mutate({ id: 42, data: { name: "Ana Updated" } });
```

#### ✅ REQUIRED
- Use the `baseUrl` pattern (e.g., `"/users/"`) — the hook appends `/{id}/`
- Always use `UpdateVariables<TPayload>` shape: `{ id: number|string, data: TPayload }`
- Spread `buildApiPayload` via the hook for payload construction

#### ❌ FORBIDDEN
- Hardcoding full URLs like `"/users/42/"` — use `baseUrl` + `id` instead
- Manual `try/catch` in components for error handling — the hook manages this
- Calling `api.request` or `api.put` directly — bypasses the abstraction

---

### `useApiDelete`

**Purpose**: Deletes a resource by ID using the `baseUrl` + `id` pattern with automatic confirmation toast on error.

```typescript
const deleteUser = useApiDelete<User>({
  baseUrl: "/users/",
});

deleteUser.mutate(42);
```

#### ✅ REQUIRED
- Use `baseUrl` pattern — the hook constructs `DELETE /{baseUrl}/{id}/`
- The mutation variable is just the `id` (number or string), not an object
- Pass `onSuccess` callback via `options` for post-delete actions (e.g., invalidating query cache)

#### ❌ FORBIDDEN
- Passing full URLs with IDs hardcoded — the hook appends the ID automatically
- Manual error handling with `try/catch` — the hook emits toast notifications
- Calling `api.delete` directly — bypasses the abstraction and error handling

---

## System Hooks (3)

### `useDebounce`

**Purpose**: Delays a value by a specified time to avoid rapid updates (typically used for search inputs).

```typescript
const [searchTerm, setSearchTerm] = useState("");
const debouncedSearch = useDebounce(searchTerm, 300);

// Use debouncedSearch for API calls — not searchTerm
```

#### ✅ REQUIRED
- Use a delay of at least 300ms for search/filter inputs
- Use for any value that triggers expensive operations (API calls, computations)
- The debounced value is always the return value — not the original

#### ❌ FORBIDDEN
- Using `setTimeout` directly in components — use this hook instead
- Using delays under 300ms — defeats the purpose of debouncing
- Using the non-debounced value for API calls — defeats the purpose

---

### `usePagination`

**Purpose**: Manages page and page size state for paginated data, resetting to page 1 when page size changes.

```typescript
const { page, pageSize, onPageChange, onPageSizeChange, paginationParams } = usePagination({
  initialPage: 1,
  initialPageSize: 10,
});

// Spread paginationParams into useApiQuery params
const { data } = useApiQuery({
  url: "/users/",
  params: paginationParams, // { page: 1, page_size: 10 }
});
```

#### ✅ REQUIRED
- Always spread `paginationParams` into `useApiQuery.params` — never manually construct page params
- Use `onPageChange` and `onPageSizeChange` callbacks — never mutate state directly
- When `pageSize` changes, the hook automatically resets `page` to 1

#### ❌ FORBIDDEN
- Using `useState` for page/pageSize manually — use this hook instead
- Mutating `page` or `pageSize` directly — use the callbacks only
- Forgetting to spread `paginationParams` — results in missing `page` and `page_size` params

---

### `useIsMobile`

**Purpose**: Detects mobile viewport width (< 768px) via `matchMedia`, updating on window resize.

```typescript
const isMobile = useIsMobile();

return (
  <div>
    {isMobile ? <MobileLayout /> : <DesktopLayout />}
  </div>
);
```

#### ✅ REQUIRED
- Use only for JavaScript-dependent responsive behavior (e.g., which layout to render)
- The hook returns `false` until the effect runs, then returns the correct value
- Use for component-level responsive logic — not CSS-solvable layouts

#### ❌ FORBIDDEN
- Using for CSS-solvable layouts — use Tailwind CSS responsive classes instead
- Relying on the initial `undefined` state for critical logic — account for the loading state
- Hardcoding breakpoint values that differ from the 768px constant

---

## Architecture Notes

### Barrel Exports
Only 6 of 7 hooks are exported via `next/src/hooks/index.ts`:
- `useApiCreate`, `useApiDelete`, `useApiQuery`, `useApiUpdate` (API hooks)
- `usePagination`, `useDebounce` (System hooks)

`useIsMobile` is **not** in the barrel and must be imported directly from `@/hooks/use-mobile`.

### Error Handling Convention
All API hooks emit error toasts via `notify.error()` when `showToast: true` (default). Components should not add redundant error handling.

### Payload Building
`useApiCreate` and `useApiUpdate` use `buildApiPayload` internally. This function detects `File`/`Blob` fields and wraps the payload in `FormData` when needed — components never call it directly.
