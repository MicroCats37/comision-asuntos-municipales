# Breadcrumbs: Inputs & Outputs

## Component API

### Breadcrumbs Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `items` | `BreadcrumbSegment[]` | Yes | — | Array of breadcrumb segments |
| `className` | `string` | No | `""` | CSS class for wrapper |

### BreadcrumbSegment Interface

```typescript
interface BreadcrumbSegment {
  label: string;
  href?: string;
  icon?: ReactNode;
}
```

**Rules:**
- If `href` is provided → render as clickable link
- If `href` is omitted → render as plain text (current page)
- `icon` is optional and renders before the label

## Data Contracts

### Segment Array Convention

```typescript
// Always end with the current page (no href)
const items: BreadcrumbSegment[] = [
  { label: 'Inicio', href: '/' },
  { label: 'Productos', href: '/productos' },
  { label: 'Zapatilla Nike' },  // Current page — no href
];
```

### With Icons

```typescript
import { Home, Package } from 'lucide-react';

const items: BreadcrumbSegment[] = [
  { label: 'Inicio', href: '/', icon: <Home className="w-4 h-4" /> },
  { label: 'Productos', href: '/productos', icon: <Package className="w-4 h-4" /> },
  { label: 'Zapatilla Nike' },
];
```

## See Also
- [Spec: Breadcrumbs](./SPEC.md) — full spec
