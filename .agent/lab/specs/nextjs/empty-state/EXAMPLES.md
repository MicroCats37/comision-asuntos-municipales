# Empty State: Worked Examples

## Example 1: Table Empty State

Displaying when a data table has no rows:

```tsx
import { EmptyState } from "@/components/emptyState/EmptyState";
import { Table3 } from "lucide-react";
import { Button } from "@/components/ui/button";

export function UsersTable() {
  const { data: users } = useUsers();

  if (!users?.length) {
    return (
      <EmptyState
        icon={<Table3 className="h-8 w-8" />}
        title="No users yet"
        description="Create your first user to get started"
        action={<Button>Create User</Button>}
      />
    );
  }

  return <DataTable data={users} />;
}
```

## Example 2: Card Empty State

Displaying when a card collection is empty:

```tsx
import { EmptyState } from "@/components/emptyState/EmptyState";
import { Package } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export function ProductGrid() {
  const { data: products } = useProducts();

  if (!products?.length) {
    return (
      <Card>
        <CardContent className="p-0">
          <EmptyState
            icon={<Package className="h-8 w-8" />}
            title="No products"
            description="Add your first product to start selling"
          />
        </CardContent>
      </Card>
    );
  }

  return <ProductGrid data={products} />;
}
```

## Example 3: Search No Results with Action

Displaying when a search yields no results:

```tsx
import { EmptyState } from "@/components/emptyState/EmptyState";
import { SearchX } from "lucide-react";
import { Button } from "@/components/ui/button";

export function SearchResults({ query }: { query: string }) {
  const { data: results } = useSearch(query);

  if (results?.length === 0) {
    return (
      <EmptyState
        icon={<SearchX className="h-8 w-8" />}
        title={`No results for "${query}"`}
        description="Try different keywords or check your spelling"
        action={
          <Button variant="outline" onClick={() => clearFilters()}>
            Clear filters
          </Button>
        }
      />
    );
  }

  return <SearchResultList results={results} />;
}
```

## Example 4: Minimal Empty State

Simple icon and title only:

```tsx
import { EmptyState } from "@/components/emptyState/EmptyState";
import { MessageSquare } from "lucide-react";

export function CommentsList() {
  const { data: comments } = useComments();

  if (!comments?.length) {
    return (
      <EmptyState
        icon={<MessageSquare className="h-8 w-8" />}
        title="No comments yet"
      />
    );
  }

  return <CommentList comments={comments} />;
}
```

## See Also
- [Spec: Empty State](./SPEC.md) — full spec
- [IO: Empty State](./IO.md) — component API