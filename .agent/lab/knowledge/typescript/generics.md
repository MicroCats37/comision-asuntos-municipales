# TypeScript: Advanced Generics

## What is it
Generics allow creating components and functions that work with multiple types without losing type safety, acting as "type variables".

## Golden Rules
- ✅ DO: Use Generics for "Lego" UI components (Tables, Selects, Modals) that handle variable data shapes.
- ✅ DO: Extend base types when needed (e.g., `<T extends Record<string, any>>`) to ensure the generic has certain properties.
- ❌ DON'T: Overload a single component with too many generics. If you need more than 2 or 3, consider splitting the component.

## Canonical Code

```typescript
// 1. Generic List Component 
interface ListProps<T> {
  items: T[];
  renderItem: (item: T) => React.ReactNode;
  keyExtractor: (item: T) => string | number;
}

export function GenericList<T>({ items, renderItem, keyExtractor }: ListProps<T>) {
  return (
    <ul>
      {items.map((item) => (
        <li key={keyExtractor(item)}>{renderItem(item)}</li>
      ))}
    </ul>
  );
}

// 2. Generic API Function
async function fetchData<T>(url: string): Promise<T> {
  const response = await fetch(url);
  return response.json() as T;
}
```

## Gotchas
- TypeScript sometimes cannot infer the generic in React components if initial props aren't passed; in those cases, declare it explicitly: `<GenericList<User> ... />`.
- In `.tsx` files, a simple generic `<T>` can be confused with an HTML tag. Solution: use `<T,>` or `<T extends unknown>`.