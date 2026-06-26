# Breadcrumbs: Worked Examples

## Example 1: Simple Page Hierarchy

Basic three-level breadcrumb for a product detail page:

```tsx
import { Breadcrumbs } from "@/components/ui/breadcrumbs";

export function ProductBreadcrumb() {
  return (
    <Breadcrumbs items={[
      { label: 'Inicio', href: '/' },
      { label: 'Productos', href: '/productos' },
      { label: 'Detalle' },
    ]} />
  );
}
```

## Example 2: With Icons

E-commerce breadcrumb with category icons:

```tsx
import { Home, Package, Tag } from 'lucide-react';
import { Breadcrumbs } from "@/components/ui/breadcrumbs";

export function CategoryBreadcrumb() {
  return (
    <Breadcrumbs items={[
      { label: 'Inicio', href: '/', icon: <Home className="w-4 h-4" /> },
      { label: 'Productos', href: '/productos', icon: <Package className="w-4 h-4" /> },
      { label: 'Zapatillas', href: '/productos/zapatillas' },
      { label: 'Nike Air Max', icon: <Tag className="w-4 h-4" /> },
    ]} />
  );
}
```

## Example 3: Admin Settings

Multi-level admin breadcrumb:

```tsx
import { Settings, User, Shield } from 'lucide-react';
import { Breadcrumbs } from "@/components/ui/breadcrumbs";

export function AdminBreadcrumb() {
  return (
    <Breadcrumbs items={[
      { label: 'Dashboard', href: '/admin' },
      { label: 'Usuarios', href: '/admin/users' },
      { label: 'Configuración', href: '/admin/users/settings' },
      { label: 'Seguridad' },
    ]} />
  );
}
```

## Example 4: Dynamic Labels

Using dynamic data for breadcrumb labels:

```tsx
import { Breadcrumbs } from "@/components/ui/breadcrumbs";

interface BreadcrumbProps {
  category: string;
  product: string;
}

export function DynamicBreadcrumb({ category, product }: BreadcrumbProps) {
  return (
    <Breadcrumbs items={[
      { label: 'Inicio', href: '/' },
      { label: category, href: `/category/${category.toLowerCase()}` },
      { label: product },
    ]} />
  );
}
```

## See Also
- [Spec: Breadcrumbs](./SPEC.md) — full spec
