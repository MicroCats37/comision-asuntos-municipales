# Hooks — Usage Examples

## API Hooks

---

### `useApiQuery` — Fetching a Paginated List

```typescript
import { useApiQuery } from "@/hooks";
import { UserSchema, type User } from "@/schemas/user";

interface UsersQueryParams {
  search?: string;
}

function UsersList({ search }: UsersQueryParams) {
  const { data: users, isLoading, error } = useApiQuery<User[], User[]>({
    queryKey: ["users", "list", search],
    url: "/users/",
    schema: UserSchema,
    params: { search, page: 1, page_size: 10 },
  });

  if (isLoading) return <Skeleton />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <ul>
      {users?.map((user) => (
        <li key={user.id}>{user.name}</li>
      ))}
    </ul>
  );
}
```

**Conditional query (url = null disables)**:

```typescript
function OptionalData({ enabled }: { enabled: boolean }) {
  const { data } = useApiQuery({
    queryKey: ["optional-data"],
    url: enabled ? "/optional/" : null,
    schema: OptionalSchema,
  });

  return <div>{data?.content}</div>;
}
```

---

### `useApiCreate` — Creating a Resource with File Upload

```typescript
import { useApiCreate } from "@/hooks";
import { useQueryClient } from "@tanstack/react-query";
import { UserSchema, type User, type CreateUserPayload } from "@/schemas/user";

function CreateUserForm() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [avatar, setAvatar] = useState<File | null>(null);

  const createUser = useApiCreate<User, CreateUserPayload>({
    url: "/users/",
    schema: UserSchema,
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["users"] });
      },
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    // buildApiPayload is called internally — File fields auto-detected
    createUser.mutate({ name, avatar });
  };

  return (
    <form onSubmit={handleSubmit}>
      <input value={name} onChange={(e) => setName(e.target.value)} />
      <input type="file" onChange={(e) => setAvatar(e.target.files?.[0] ?? null)} />
      <button type="submit" disabled={createUser.isPending}>
        {createUser.isPending ? "Creating..." : "Create User"}
      </button>
    </form>
  );
}
```

---

### `useApiUpdate` — Editing an Existing Resource

```typescript
import { useApiUpdate } from "@/hooks";
import { useQueryClient } from "@tanstack/react-query";
import { UserSchema, type User, type UpdateUserPayload } from "@/schemas/user";

function EditUserForm({ userId }: { userId: number }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");

  const updateUser = useApiUpdate<User, UpdateUserPayload>({
    baseUrl: "/users/",
    schema: UserSchema,
    method: "PUT", // or "PATCH"
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["users", "list"] });
        queryClient.invalidateQueries({ queryKey: ["users", userId] });
      },
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    // UpdateVariables shape: { id, data }
    updateUser.mutate({ id: userId, data: { name } });
  };

  return (
    <form onSubmit={handleSubmit}>
      <input value={name} onChange={(e) => setName(e.target.value)} />
      <button type="submit" disabled={updateUser.isPending}>
        {updateUser.isPending ? "Saving..." : "Save Changes"}
      </button>
    </form>
  );
}
```

---

### `useApiDelete` — Deleting with Confirmation

```typescript
import { useApiDelete } from "@/hooks";
import { useQueryClient } from "@tanstack/react-query";
import { UserSchema } from "@/schemas/user";

function DeleteUserButton({ userId }: { userId: number }) {
  const queryClient = useQueryClient();

  const deleteUser = useApiDelete<User>({
    baseUrl: "/users/",
    options: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["users"] });
        // Toast shown automatically on error (showToast: true by default)
      },
    },
  });

  const handleDelete = () => {
    if (window.confirm("Are you sure you want to delete this user?")) {
      // Pass id directly — not { id } object
      deleteUser.mutate(userId);
    }
  };

  return (
    <button
      onClick={handleDelete}
      disabled={deleteUser.isPending}
      className="text-red-600"
    >
      {deleteUser.isPending ? "Deleting..." : "Delete"}
    </button>
  );
}
```

---

## System Hooks

---

### `useDebounce` — Search Input Debouncing

```typescript
import { useDebounce } from "@/hooks";
import { useApiQuery } from "@/hooks";
import { SearchSchema, type SearchResult } from "@/schemas/search";
import { useState } from "react";

function SearchPage() {
  const [query, setQuery] = useState("");
  // Debounce the query by 300ms to avoid excessive API calls
  const debouncedQuery = useDebounce(query, 300);

  const { data: results } = useApiQuery<SearchResult[]>({
    queryKey: ["search", debouncedQuery],
    url: "/search/",
    schema: SearchSchema,
    params: { q: debouncedQuery },
    // Disable when debounced query is empty
    queryOptions: { enabled: debouncedQuery.length > 0 },
  });

  return (
    <div>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search..."
        className="border p-2 rounded"
      />
      <p className="text-sm text-gray-500 mt-1">
        Results update after you stop typing...
      </p>
      <ul>
        {results?.map((r) => (
          <li key={r.id}>{r.title}</li>
        ))}
      </ul>
    </div>
  );
}
```

---

### `usePagination` — Table Pagination State

```typescript
import { usePagination, useApiQuery } from "@/hooks";
import { UserSchema, type User } from "@/schemas/user";

function UsersTable() {
  const {
    page,
    pageSize,
    onPageChange,
    onPageSizeChange,
    paginationParams,
  } = usePagination({ initialPage: 1, initialPageSize: 10 });

  const { data, isLoading } = useApiQuery<User[]>({
    queryKey: ["users", "table", page, pageSize],
    url: "/users/",
    schema: UserSchema,
    params: paginationParams, // { page: 1, page_size: 10 }
  });

  return (
    <div>
      <table className="w-full">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
          </tr>
        </thead>
        <tbody>
          {data?.map((user) => (
            <tr key={user.id}>
              <td>{user.name}</td>
              <td>{user.email}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="flex gap-4 items-center mt-4">
        <select
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          className="border p-1"
        >
          <option value={10}>10 per page</option>
          <option value={25}>25 per page</option>
          <option value={50}>50 per page</option>
        </select>

        <div className="flex gap-2">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page === 1}
          >
            Previous
          </button>
          <span>Page {page}</span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={data && data.length < pageSize}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

### `useIsMobile` — Conditional Rendering Mobile/Desktop

```typescript
// Note: Must import directly — not in barrel export
import { useIsMobile } from "@/hooks/use-mobile";

function ResponsiveLayout() {
  const isMobile = useIsMobile();

  return (
    <div className={isMobile ? "flex-col" : "flex-row"}>
      <header className={isMobile ? "mobile-header" : "desktop-header"}>
        {isMobile ? <MobileNav /> : <DesktopNav />}
      </header>
      <main>
        {isMobile ? <MobileProductGrid /> : <DesktopProductGrid />}
      </main>
      {isMobile && <FloatingActionButton />}
    </div>
  );
}
```

**With SSR-safe initial state handling**:

```typescript
function ResponsiveComponent() {
  const isMobile = useIsMobile();

  // Handle the initial undefined state
  if (isMobile === undefined) {
    return <LoadingSkeleton variant="unknown" />;
  }

  return isMobile ? <MobileView /> : <DesktopView />;
}
```

---

## Combined Example — Search with Debounce + Pagination

```typescript
import { useDebounce, usePagination, useApiQuery } from "@/hooks";
import { SearchSchema, type SearchResult } from "@/schemas/search";
import { useState } from "react";

function SearchResults() {
  const [query, setQuery] = useState("");
  const { paginationParams, ...paginationControls } = usePagination();
  const debouncedQuery = useDebounce(query, 300);

  const { data: results, isLoading, error } = useApiQuery<SearchResult[]>({
    queryKey: ["search", debouncedQuery, paginationParams],
    url: "/search/",
    schema: SearchSchema,
    params: { q: debouncedQuery, ...paginationParams },
    queryOptions: { enabled: debouncedQuery.length >= 2 },
  });

  return (
    <div>
      <input value={query} onChange={(e) => setQuery(e.target.value)} />
      {isLoading && <Spinner />}
      {!isLoading && results && (
        <>
          <p>{results.length} results found</p>
          <ul>{results.map((r) => <li key={r.id}>{r.title}</li>)}</ul>
          <div className="pagination">
            <button onClick={() => paginationControls.onPageChange(page - 1)}>
              Prev
            </button>
            <span>Page {page}</span>
            <button onClick={() => paginationControls.onPageChange(page + 1)}>
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
```
