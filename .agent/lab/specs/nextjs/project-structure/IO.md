# Project Structure: Inputs & Outputs

## Directory Structure Contract

```
src/
├── app/                        ← Routing only
│   ├── (public)/               ← Route group: public pages
│   └── (admin)/                ← Route group: admin pages
│
├── features/                   ← All business logic
│   ├── {domain}/               ← Shared domain
│   ├── admin/{domain}/         ← Admin-specific overrides
│   └── public/{domain}/         ← Public-specific overrides
│
├── components/                 ← Generic reusable UI
│   └── ui/                     ← Shadcn components
│
├── shared/                     ← Cross-feature utilities
│   ├── schemas/                ← Shared Zod schemas
│   ├── types/                   ← Shared TypeScript types
│   └── utils/                  ← Shared helpers
│
└── lib/                        ← Infrastructure only
    ├── api.ts                  ← Axios instance
    └── query-client.ts         ← TanStack Query config
```

## Feature Folder Anatomy

```
src/features/{domain}/
├── schemas/
│   ├── {action}.schema.ts     ← Named: CreateUserSchema, UpdateProductSchema
│   └── index.ts               ← Granular barrel (schemas only)
├── services/
│   ├── {action}.service.ts
│   └── index.ts               ← Granular barrel
├── hooks/
│   ├── use{Action}.ts          ← Named: useLogin, useCreateProduct
│   └── index.ts               ← Granular barrel
├── utils/
│   └── {name}.utils.ts
└── components/
    ├── {Feature}Form.tsx      ← Public UI components
    ├── {Feature}Card.tsx
    └── index.ts               ← Only public UI
```

## Naming Conventions

### Schema Exports

| File | Export | Type Export |
|------|--------|-------------|
| `schemas/login.schema.ts` | `LoginFormSchema` | `LoginFormData` |
| `schemas/product.schema.ts` | `CreateProductSchema` | `CreateProductData` |
| `schemas/product.schema.ts` | `UpdateProductSchema` | `UpdateProductData` |

### Hook Exports

| File | Export | Pattern |
|------|--------|---------|
| `hooks/useLogin.ts` | `useLogin` | `use` prefix |
| `hooks/useProduct.ts` | `useProduct` | `use` prefix |
| `hooks/useAdminProducts.ts` | `useAdminProducts` | `use` + domain prefix |

### Import Order (Enforced by Biome)

```typescript
// 1. External libraries
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";

// 2. Internal aliases (@/)
import { Button } from "@/components/ui/button";

// 3. Relative imports
import { LoginFormSchema } from "../schemas";
```

## Barrel Rules

### ✅ REQUIRED: Granular Re-exports

```typescript
// features/auth/schemas/index.ts
export { LoginFormSchema, type LoginFormData } from "./login.schema";
export { RegisterFormSchema, type RegisterFormData } from "./register.schema";
```

### ❌ FORBIDDEN: Wildcard Re-exports

```typescript
export * from "./schemas";     // ❌ Breaks tree-shaking
export * from "./hooks";        // ❌ Imports everything
```

## Type Exports

```typescript
// features/auth/schemas/index.ts
export type { LoginFormData } from "./login.schema";
export type { RegisterFormData } from "./register.schema";
```

## See Also
- [Spec: Project Structure](./SPEC.md) — full spec
- [Spec: Forms](./forms/SPEC.md) — schema conventions
- [Shared: Types](../shared/types.md) — type contract
