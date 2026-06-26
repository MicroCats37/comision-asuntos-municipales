# DataTable: Worked Examples

## Example 1: Full Page Table (mode="url") ✅ REQUIRED

Complete productos page with external filters, URL state, and shareable links:

```tsx
"use client";

import { Suspense } from "react";
import { GenericDataTable } from "@/components/genericDataTable/GenericDataTable";
import { createColumns, textColumn, numberColumn, dateColumn, badgeColumn } from "@/components/genericDataTable/columns";
import { useApiQuery } from "@/hooks/useApiQuery";
import { usePagination } from "@/hooks/usePagination";
import { PaginatedProductosSchema } from "@/features/productos/schemas";
import { EmptyState } from "@/components/ui/empty-state";

interface Producto {
  id: string;
  nombre: string;
  precio: number;
  estado: 'activo' | 'inactivo';
  createdAt: string;
}

export default function ProductosPage() {
  const { page, pageSize, onPageChange } = usePagination(20);
  const [ordering, setOrdering] = useState<string>('-created_at');

  const { data, isLoading } = useApiQuery({
    queryKey: ['productos', { page, pageSize, ordering }],
    url: '/api/productos',
    params: { page, page_size: pageSize, ordering },
    schema: PaginatedProductosSchema,
  });

  const columns = createColumns<Producto>([
    textColumn('nombre', 'Nombre', { sortable: true }),
    numberColumn('precio', 'Precio', { 
      format: (v) => `S/ ${v.toFixed(2)}` 
    }),
    dateColumn('createdAt', 'Creado', { format: 'short' }),
    badgeColumn('estado', 'Estado', {
      activo: 'bg-green-100 text-green-800',
      inactivo: 'bg-red-100 text-red-800',
    }),
  ]);

  return (
    <Suspense>
      <GenericDataTable<Producto>
        columns={columns}
        data={data?.data ?? []}
        isLoading={isLoading}
        mode="url"
        pagination={{
          page,
          pageSize,
          totalPages: data?.totalPages ?? 0,
          totalItems: data?.count ?? 0,
        }}
        onPaginationChange={onPageChange}
        onSortingChange={(sort) => {
          setOrdering(
            sort
              ? `${sort.direction === 'desc' ? '-' : ''}${sort.field}`
              : ''
          );
        }}
        emptyState={<EmptyState message="No hay productos" />}
      />
    </Suspense>
  );
}
```

**Key patterns:**
- External `usePagination` and `useState` for ordering
- `useApiQuery` fetches data — GenericDataTable never fetches
- `createColumns<Producto>()` with typed helpers
- `mode="url"` enables shareable URLs
- Wrap in `<Suspense>` (required for mode="url")

---

## Example 2: Embedded Table (mode="local") inside a Card

Table embedded within a card for dashboard overview:

```tsx
"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { GenericDataTable } from "@/components/genericDataTable/GenericDataTable";
import { createColumns, textColumn, badgeColumn, actionsColumn } from "@/components/genericDataTable/columns";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";

interface RecentOrder {
  id: string;
  customer: string;
  total: number;
  status: 'pending' | 'shipped' | 'delivered';
  createdAt: string;
}

interface OrdersCardProps {
  orders: RecentOrder[];
  isLoading?: boolean;
}

export function RecentOrdersCard({ orders, isLoading }: OrdersCardProps) {
  const columns = createColumns<RecentOrder>([
    textColumn('customer', 'Cliente'),
    textColumn('total', 'Total', {
      format: (v) => `$${v.toFixed(2)}`,
    }),
    badgeColumn('status', 'Estado', {
      pending: 'bg-yellow-100 text-yellow-800',
      shipped: 'bg-blue-100 text-blue-800',
      delivered: 'bg-green-100 text-green-800',
    }),
    actionsColumn([
      {
        label: 'Ver',
        onClick: (order) => router.push(`/orders/${order.id}`),
      },
      {
        label: 'Eliminar',
        onClick: (order) => deleteOrder(order.id),
        variant: 'destructive',
      },
    ]),
  ]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Órdenes Recientes</CardTitle>
      </CardHeader>
      <CardContent>
        <GenericDataTable<RecentOrder>
          columns={columns}
          data={orders}
          isLoading={isLoading}
          mode="local"
          pagination={{
            page: 1,
            pageSize: 5,
            totalPages: 1,
            totalItems: orders.length,
          }}
          onPaginationChange={() => {
            // No-op for local mode with fixed page
          }}
          emptyState={<EmptyState message="No hay órdenes recientes" />}
        />
      </CardContent>
    </Card>
  );
}
```

**Key patterns:**
- `mode="local"` — no URL sync
- Embedded inside Card component
- Fixed pagination (page 1, 5 items) — no state changes
- Actions column for row operations

---

## Example 3: Table with External Filter Controls

Filters are completely separate from the table:

```tsx
"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { GenericDataTable } from "@/components/genericDataTable/GenericDataTable";
import { createColumns, textColumn, dateColumn } from "@/components/genericDataTable/columns";
import { useApiQuery } from "@/hooks/useApiQuery";
import { usePagination } from "@/hooks/usePagination";
import { PaginatedInvoicesSchema } from "@/features/invoices/schemas";

interface Invoice {
  id: string;
  client: string;
  amount: number;
  dueDate: string;
}

export default function InvoicesPage() {
  const { page, pageSize, onPageChange } = usePagination(20);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Filters are built in the query params — table never sees them
  const { data, isLoading } = useApiQuery({
    queryKey: ['invoices', { page, pageSize, status: statusFilter, q: searchQuery }],
    url: '/api/invoices',
    params: { 
      page, 
      page_size: pageSize, 
      status: statusFilter || undefined,
      q: searchQuery || undefined,
    },
    schema: PaginatedInvoicesSchema,
  });

  const columns = createColumns<Invoice>([
    textColumn('client', 'Cliente', { sortable: true }),
    textColumn('amount', 'Monto', { sortable: true }),
    dateColumn('dueDate', 'Vence', { format: 'short' }),
  ]);

  return (
    <div className="space-y-4">
      {/* Filters live OUTSIDE the table — reusable elsewhere */}
      <div className="flex gap-4">
        <Input
          placeholder="Buscar cliente..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <Select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">Todos</option>
          <option value="pending">Pendientes</option>
          <option value="paid">Pagadas</option>
        </Select>
      </div>

      <Suspense>
        <GenericDataTable<Invoice>
          columns={columns}
          data={data?.data ?? []}
          isLoading={isLoading}
          mode="url"
          pagination={{
            page,
            pageSize,
            totalPages: data?.totalPages ?? 0,
            totalItems: data?.count ?? 0,
          }}
          onPaginationChange={onPageChange}
          emptyState={<EmptyState message="No hay facturas" />}
        />
      </Suspense>
    </div>
  );
}
```

---

## See Also
- [Spec: DataTable](./SPEC.md) — full spec
- [Spec: Forms](./forms/SPEC.md) — GenericForm patterns
- [Spec: Hooks](./hooks/SPEC.md) — usePagination, useApiQuery
