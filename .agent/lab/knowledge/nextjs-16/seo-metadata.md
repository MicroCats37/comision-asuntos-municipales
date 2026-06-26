# Next.js 16: SEO & Metadata

## What is it
Native API for defining metadata (titles, descriptions, OpenGraph) statically or dynamically per page.

## Golden Rules
- ✅ DO: Define base `metadata` in the root `layout.tsx`.
- ✅ DO: Use `generateMetadata` for dynamic pages to pull titles from the database.
- ❌ DON'T: Use manual `<head>` tags unless strictly necessary for 3rd party scripts.

## Canonical Code

```tsx
// app/products/[id]/page.tsx
import { Metadata } from 'next';

export async function generateMetadata({ params }): Promise<Metadata> {
  const product = await getProduct(params.id);
  
  return {
    title: product.name,
    description: `Buy ${product.name} at the best price.`,
    openGraph: {
      images: [product.image],
    },
  };
}

export default function Page() { /* ... */ }
```

## Gotchas
- `generateMetadata` can only be used in Server Components.
- Next.js waits for metadata resolution before rendering, ensuring crawlers see correct info.