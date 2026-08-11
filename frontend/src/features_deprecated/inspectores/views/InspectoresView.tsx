"use client";

import { ShieldCheck } from "lucide-react";
import { type ColumnDef } from "@tanstack/react-table";
import { AppDataTable } from "@/components-app/tables/AppDataTable";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { useInspectores } from "../hooks/useInspectores";
import { useInspectoresUIStore } from "../store/inspectores-ui.store";
import type { InspectorOut } from "../types/inspectores.types";

// ── Column Definitions ────────────────────────────────────────────────────────

const columns: ColumnDef<InspectorOut>[] = [
  {
    accessorKey: "perfil_ingeniero.cip",
    header: "CIP",
    cell: ({ row }) => (
      <span className="font-mono text-sm font-semibold">
        {row.original.perfil_ingeniero.cip}
      </span>
    ),
  },
  {
    accessorKey: "perfil_ingeniero.dni",
    header: "DNI",
    cell: ({ row }) => (
      <span className="font-mono text-sm">
        {row.original.perfil_ingeniero.dni}
      </span>
    ),
  },
  {
    accessorKey: "perfil_ingeniero.nombre_completo",
    header: "Nombre Completo",
    cell: ({ row }) => (
      <span className="font-medium">
        {row.original.perfil_ingeniero.nombre_completo}
      </span>
    ),
  },
];

// ── View Component ────────────────────────────────────────────────────────────

/**
 * Vista de Inspectores — tabla con paginación.
 *
 * Usa `useInspectoresUIStore` para estado de UI (página, tamaño de página).
 * No hay botón "Nuevo" — no existe endpoint de creación.
 */
export function InspectoresView() {
  // UI Store — pagination state
  const page = useInspectoresUIStore((s) => s.page);
  const pageSize = useInspectoresUIStore((s) => s.pageSize);

  // Data fetching
  const {
    items,
    total,
    isLoading,
    isError,
    refetch,
  } = useInspectores({
    page,
    pageSize,
  });

  // AppDataTable uses 0-based pageIndex; store uses 1-based page
  const paginationState = {
    pageIndex: page - 1,
    pageSize,
  };

  const handlePaginationChange = (pagination: { pageIndex: number; pageSize: number }) => {
    useInspectoresUIStore.getState().setPage(pagination.pageIndex + 1);
  };

  return (
    <div className="page-section">
      <div className="space-y-6">
        {/* Page Header */}
        <PageHeader
          title="Inspectores"
          description="Lista de inspectores registrados"
          icon={ShieldCheck}
        />

        {/* Data Table */}
        <AppDataTable
          columns={columns}
          data={items}
          isLoading={isLoading}
          isError={isError}
          onRetry={refetch}
          pagination={paginationState}
          onPaginationChange={handlePaginationChange}
          showPagination={true}
          rowCount={total}
          emptyMessage="No hay inspectores registrados"
          emptyDescription="No se encontraron inspectores en el sistema."
          emptyIcon={<ShieldCheck className="h-10 w-10 text-muted-foreground" />}
        />
      </div>
    </div>
  );
}
