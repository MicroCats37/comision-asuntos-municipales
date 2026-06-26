# Tabs: Worked Examples

## Example 1: Local State Tabs

Basic tabs with local state for a product detail page:

```tsx
"use client";

import { GenericTabs } from "@/components/ui/generic-tabs";
import { ProductInfo } from "./ProductInfo";
import { ProductHistory } from "./ProductHistory";
import { ProductReviews } from "./ProductReviews";

export function ProductTabs() {
  return (
    <GenericTabs
      tabs={[
        { value: "info", label: "Información", content: <ProductInfo /> },
        { value: "history", label: "Historial", content: <ProductHistory /> },
        { value: "reviews", label: "Reseñas", content: <ProductReviews /> },
      ]}
      defaultTab="info"
    />
  );
}
```

## Example 2: URL-Synced Tabs

Tabs that persist selection in URL for shareability:

```tsx
"use client";

import { Suspense } from "react";
import { GenericTabs } from "@/components/ui/generic-tabs";
import { OverviewTab } from "./OverviewTab";
import { AnalyticsTab } from "./AnalyticsTab";
import { ActivityTab } from "./ActivityTab";

export function DashboardTabs() {
  return (
    <Suspense fallback={<div>Cargando...</div>}>
      <GenericTabs
        tabs={[
          { value: "overview", label: "Resumen", content: <OverviewTab /> },
          { value: "analytics", label: "Analíticas", content: <AnalyticsTab /> },
          { value: "activity", label: "Actividad", content: <ActivityTab /> },
        ]}
        syncUrl
        paramName="vista"
      />
    </Suspense>
  );
}
```

## Example 3: With Disabled Tab

Tabs where one option is conditionally disabled:

```tsx
"use client";

import { GenericTabs } from "@/components/ui/generic-tabs";
import { PublicTab } from "./PublicTab";
import { AdminTab } from "./AdminTab";

interface SettingsTabsProps {
  isAdmin: boolean;
}

export function SettingsTabs({ isAdmin }: SettingsTabsProps) {
  return (
    <GenericTabs
      tabs={[
        { value: "public", label: "Público", content: <PublicTab /> },
        { value: "admin", label: "Administrador", content: <AdminTab />, disabled: !isAdmin },
      ]}
      defaultTab="public"
    />
  );
}
```

## Example 4: Inline Content

Using inline JSX for simple tab content:

```tsx
"use client";

import { GenericTabs } from "@/components/ui/generic-tabs";

export function SimpleTabs() {
  return (
    <GenericTabs
      tabs={[
        {
          value: "description",
          label: "Descripción",
          content: (
            <div className="prose">
              <p>Este producto está fabricado con materiales de alta calidad.</p>
            </div>
          ),
        },
        {
          value: "shipping",
          label: "Envío",
          content: (
            <div>
              <h3>Política de Envío</h3>
              <p>Entrega en 3-5 días hábiles.</p>
            </div>
          ),
        },
      ]}
    />
  );
}
```

## Example 5: Data Fetched at Parent Level

Fetching data in parent and passing to tab content:

```tsx
"use client";

import { GenericTabs } from "@/components/ui/generic-tabs";
import { useProducts } from "@/hooks/useProducts";
import { ProductList } from "./ProductList";
import { ProductGrid } from "./ProductGrid";

export function ProductsView() {
  const { data: products, isLoading } = useProducts();

  return (
    <GenericTabs
      tabs={[
        { value: "list", label: "Lista", content: <ProductList products={products} /> },
        { value: "grid", label: "Cuadrícula", content: <ProductGrid products={products} /> },
      ]}
      defaultTab="grid"
    />
  );
}
```

## See Also
- [Spec: Tabs](./SPEC.md) — full spec
