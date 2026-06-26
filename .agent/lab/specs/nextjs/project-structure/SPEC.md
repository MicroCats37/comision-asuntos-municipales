# Next.js Project Structure Spec

## Metadata
- Version: 1.0
- Stack: Next.js 16 + React 19 + TypeScript
- Scope: Folder architecture, import conventions, naming rules

---

## Core Principle

> `app/` is for **routing only**. `src/features/` is for **business logic**.

The `app/` directory handles routing, layouts, and page composition.
All reusable logic (hooks, services, schemas) lives in `src/features/`.

---

## Folder Structure

```
src/
├── app/                        ← Routing only
│   ├── (public)/               ← Route group: public pages
│   │   └── products/
│   │       ├── page.tsx        ← Thin: imports from features
│   │       ├── loading.tsx
│   │       └── _components/    ← Page-specific UI only (no logic)
│   └── (admin)/                ← Route group: admin pages
│       └── products/
│           ├── page.tsx
│           └── _components/
│
├── features/                   ← All business logic
│   ├── products/               ← Shared domain logic
│   ├── admin/
│   │   └── products/           ← Admin-specific overrides
│   └── public/
│       └── products/           ← Public-specific logic
│
├── components/                 ← Generic reusable UI (Legos)
│   └── ui/
│       ├── button.tsx
│       └── input.tsx
│
├── shared/                     ← Cross-feature business logic
│   ├── schemas/                ← pagination.schema.ts, error.schema.ts
│   ├── types/                  ← ApiResponse<T>, PaginatedResult<T>
│   └── utils/                  ← helpers used by 2+ features
│
└── lib/                        ← Infrastructure only
    ├── api.ts                  ← Axios instance (used by all services)
    └── query-client.ts         ← TanStack Query client config
```

---

## Feature Folder Anatomy

Every feature follows this internal structure:

```
src/features/auth/
├── schemas/
│   ├── login.schema.ts
│   ├── register.schema.ts
│   └── index.ts               ← barrel (internal only)
├── services/
│   ├── login.service.ts
│   ├── register.service.ts
│   └── index.ts
├── hooks/
│   ├── useLogin.ts
│   ├── useRegister.ts
│   └── index.ts
├── utils/
│   ├── auth.utils.ts
│   └── index.ts
└── components/
    ├── LoginForm.tsx
    └── index.ts               ← only public UI exposed here
```

---

## Naming Conventions

| Layer | File | Export | Type export |
|-------|------|--------|-------------|
| Schema | `login.schema.ts` | `LoginFormSchema` | `LoginFormData` |
| Schema (API) | `login.schema.ts` | `LoginResponseSchema` | `LoginResponse` |
| Service | `login.service.ts` | `loginUser()` | — |
| Hook | `useLogin.ts` | `useLogin()` | — |
| Utils | `auth.utils.ts` | `formatAuthError()` | — |
| Component | `LoginForm.tsx` | `LoginForm` | `LoginFormProps` |

### Schema Naming by Operation
```ts
// Form schemas (client-side)
LoginFormSchema       → LoginFormData
RegisterFormSchema    → RegisterFormData

// API schemas (server contracts)
CreateProductSchema   → CreateProductData    // POST body
UpdateProductSchema   → UpdateProductData    // PATCH body
ProductResponseSchema → ProductResponse      // GET response
```

---

## Import Conventions

### ✅ REQUIRED: Named Imports Always
```ts
import { useState, useRef } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { z } from "zod";
```

### ❌ FORBIDDEN: Default / Namespace Imports
```ts
import React from "react";          // ❌ React 18 pattern
import * as React from "react";     // ❌ Never
import * as z from "zod";           // ❌ Never
```

### Import Order (enforced by Biome)
```ts
// 1. External libraries
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";

// 2. Internal aliases (@/)
import { Button } from "@/components/ui/button";

// 3. Relative imports
import { LoginFormSchema } from "../schemas";
import { loginUser } from "../services";
```

---

## Barrel Rules

### ✅ REQUIRED: Granular re-exports only
```ts
// features/auth/schemas/index.ts
export { LoginFormSchema, type LoginFormData } from "./login.schema";
export { RegisterFormSchema, type RegisterFormData } from "./register.schema";

// features/auth/index.ts — only exposes public UI
export { LoginForm } from "./components";
// ❌ DO NOT re-export schemas, hooks, services from feature root
```

### ❌ FORBIDDEN: Wildcard re-exports
```ts
export * from "./schemas";     // ❌ breaks tree-shaking
export * from "./hooks";       // ❌ imports everything
export * from "./services";    // ❌ never
```

### Barrel Depth Rules
| Level | Barrel Allowed? | Rule |
|-------|----------------|------|
| `features/auth/schemas/index.ts` | ✅ Yes | Granular named exports |
| `features/auth/index.ts` | ✅ Yes | Only public UI components |
| `features/index.ts` | ❌ Never | No global feature barrel |
| `components/ui/index.ts` | ✅ Yes | Granular named exports |
| `components/index.ts` | ❌ Never | No global component barrel |

---

## Admin vs Public: Choosing Your Strategy

When a domain exists in both admin and public contexts, choose based on logic overlap:

### Option A — Namespaced Features (DEFAULT)
Use when admin and public have **different endpoints, permissions, or schemas**.

```
src/features/
├── products/              ← shared types only (if any)
├── admin/
│   └── products/          ← full CRUD + permissions
└── public/
    └── products/          ← read-only + filters
```

```ts
// app/(admin)/products/page.tsx
import { useAdminProducts } from "@/features/admin/products/hooks";

// app/(public)/products/page.tsx
import { usePublicProducts } from "@/features/public/products/hooks";
```

### Option B — Single Feature with Variants
Use when admin and public **share >70% of logic** (same endpoints, different UI).

```
src/features/products/
├── schemas/
│   ├── product-public.schema.ts
│   └── product-admin.schema.ts
├── hooks/
│   ├── usePublicProducts.ts
│   └── useAdminProducts.ts
└── services/
    └── products.service.ts    ← shared service
```

### Decision Criteria
| Condition | Choose |
|-----------|--------|
| Different API endpoints | Option A |
| Different permission logic | Option A |
| Same endpoint, different display | Option B |
| Shared mutations (admin creates, public reads same data) | Option B |
| Large domain with many sub-features | Option A |

---

## Shared Layer Rules

Use `src/shared/` for code that crosses feature boundaries.

| Rule | Description |
|------|-------------|
| **2+ features rule** | Only move to `shared/` when 2+ features need it |
| **No business logic in `lib/`** | `lib/` = infrastructure setup only (Axios, QueryClient) |
| **Services call `lib/api.ts`** | All feature services import the Axios instance from `@/lib/api` |
| **Small project exception** | Until 3+ features exist, `lib/` can temporarily hold shared schemas |

```ts
// ✅ shared/schemas/pagination.schema.ts
export const PaginationSchema = z.object({
  page: z.number().int().min(1),
  limit: z.number().int().min(1).max(100),
});
export type Pagination = z.infer<typeof PaginationSchema>;

// ✅ shared/types/api.types.ts
export type ApiResponse<T> = {
  data: T;
  message: string;
  success: boolean;
};

// ✅ lib/api.ts — infrastructure only
export const api = axios.create({ baseURL: process.env.NEXT_PUBLIC_API_URL });
```

---

## `app/_components/` Rules

Private page-level components (underscore prefix = not routable in Next.js).

### ✅ Use for:
- Layout-specific compositions unique to that page
- Visual wrappers that have no business logic
- Static or near-static content

### ❌ Do NOT put here:
- Components that use custom hooks
- Anything that calls a service or schema
- Components reused in more than one page

```tsx
// ✅ OK in app/(admin)/dashboard/_components/DashboardHeader.tsx
export function DashboardHeader({ title }: { title: string }) {
  return <header><h1>{title}</h1></header>;
}

// ❌ Should be in features/ instead (has business logic)
export function DashboardHeader() {
  const { user } = useCurrentUser();         // hook → belongs in features/
  return <header><h1>{user.name}</h1></header>;
}
```
