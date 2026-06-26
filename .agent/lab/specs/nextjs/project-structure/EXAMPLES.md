# Project Structure: Worked Examples

## Example 1: Creating a New Feature

Full structure for a `products` feature:

```typescript
// src/features/products/schemas/index.ts
export { CreateProductFormSchema, type CreateProductData } from "./product.schema";
export { UpdateProductFormSchema, type UpdateProductData } from "./product.schema";
export { ProductResponseSchema, type ProductResponse } from "./product.schema";

// src/features/products/hooks/index.ts
export { useProducts } from "./useProducts";
export { useCreateProduct } from "./useCreateProduct";
export { useUpdateProduct } from "./useUpdateProduct";

// src/features/products/components/ProductForm.tsx
export function ProductForm() {
  // Implementation
}

// src/features/products/components/index.ts
export { ProductForm } from "./ProductForm";

// src/features/products/index.ts — ONLY public UI
export { ProductForm } from "./components";
```

## Example 2: Admin vs Public Separation

When domains have different endpoints or permissions:

```
src/features/
├── products/                   ← Shared types only (interfaces, base schemas)
│   └── types/product.ts
├── admin/
│   └── products/              ← Full CRUD, all permissions
│       ├── schemas/
│       ├── services/
│       ├── hooks/
│       │   ├── useAdminProducts.ts
│       │   └── useCreateProduct.ts
│       └── components/
└── public/
    └── products/              ← Read-only + filters
        ├── schemas/
        ├── services/
        ├── hooks/
        │   └── usePublicProducts.ts
        └── components/
```

```typescript
// app/(admin)/products/page.tsx
import { useAdminProducts } from "@/features/admin/products/hooks";

// app/(public)/products/page.tsx
import { usePublicProducts } from "@/features/public/products/hooks";
```

## Example 3: Feature with Shared Service

When admin and public share >70% logic:

```
src/features/products/
├── schemas/
│   ├── product-admin.schema.ts
│   └── product-public.schema.ts
├── services/
│   └── products.service.ts    ← Shared service
├── hooks/
│   ├── useAdminProducts.ts
│   └── usePublicProducts.ts
└── components/
    ├── ProductCard.tsx        ← Shared UI
    └── index.ts
```

## Example 4: Correct Import Order

```typescript
// 1. External libraries (sorted)
import { useQuery, useMutation } from "@tanstack/react-query";
import { z } from "zod";
import { useRouter } from "next/navigation";

// 2. Internal aliases (@/)
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// 3. Relative imports
import { CreateProductData } from "../../schemas/product.schema";
import { createProduct } from "../../services/product.service";
```

## Example 5: Barrel File Best Practices

```typescript
// ✅ features/auth/index.ts — Only public UI
export { LoginForm } from "./components/LoginForm";
export { RegisterForm } from "./components/RegisterForm";

// ❌ features/auth/index.ts — Never export internals
export * from "./schemas";     // Breaks tree-shaking
export * from "./hooks";       // Imports everything
```

```typescript
// ✅ features/auth/schemas/index.ts — Granular exports
export { LoginFormSchema, type LoginFormData } from "./login.schema";
export { RegisterFormSchema, type RegisterFormData } from "./register.schema";

// ❌ features/auth/schemas/index.ts — Never wildcard
export * from "./login.schema";
```

## Example 6: Shared Layer Usage

```typescript
// src/shared/schemas/pagination.schema.ts
import { z } from "zod";

export const PaginationSchema = z.object({
  page: z.number().int().min(1),
  limit: z.number().int().min(1).max(100),
});

export type Pagination = z.infer<typeof PaginationSchema>;

// src/shared/types/api.types.ts
export type ApiResponse<T> = {
  data: T;
  message: string;
  success: boolean;
};

// src/lib/api.ts — Infrastructure only
import axios from "axios";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
});
```

## Example 7: app/_components Usage

```tsx
// app/(admin)/dashboard/_components/DashboardHeader.tsx
// ✅ OK: Layout-specific, no business logic
export function DashboardHeader({ title }: { title: string }) {
  return <header><h1>{title}</h1></header>;
}

// app/(admin)/dashboard/page.tsx
import { DashboardHeader } from "./_components/DashboardHeader";
```

## See Also
- [Spec: Project Structure](./SPEC.md) — full spec
- [Shared: Types](../shared/types.md) — type conventions
