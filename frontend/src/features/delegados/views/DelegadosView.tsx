"use client";

import { Users } from "lucide-react";
import { type ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { AppDataTable } from "@/components-app/tables/AppDataTable";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { useDelegados } from "../hooks/useDelegados";
import { useDelegadosUIStore } from "../store/delegados-ui.store";
import type { DelegadoOut } from "../types/delegados.types";

// ── Column Definitions ────────────────────────────────────────────────────────

const columns: ColumnDef<DelegadoOut>[] = [
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
  {
    accessorKey: "perfil_ingeniero.correo_personal",
    header: "Correo",
    cell: ({ row }) => {
      const correo = row.original.perfil_ingeniero.correo_personal
        ?? row.original.perfil_ingeniero.correo_institucional;
      return <span className="text-sm">{correo ?? "—"}</span>;
    },
  },
];

// ── View Component ────────────────────────────────────────────────────────────

/**
 * Vista de Delegados — tabla con paginación.
 *
 * Usa `useDelegadosUIStore` para estado de UI (página, tamaño de página).
 * El botón "Nuevo" está deshabilitado porque no existe endpoint de creación.
 */
export function DelegadosView() {
  // UI Store — pagination state
  const page = useDelegadosUIStore((s) => s.page);
  const pageSize = useDelegadosUIStore((s) => s.pageSize);

  // Data fetching
  const {
    items,
    total,
    isLoading,
    isError,
    refetch,
  } = useDelegados({
    page,
    pageSize,
  });

  // AppDataTable uses 0-based pageIndex; store uses 1-based page
  const paginationState = {
    pageIndex: page - 1,
    pageSize,
  };

  const handlePaginationChange = (pagination: { pageIndex: number; pageSize: number }) => {
    useDelegadosUIStore.getState().setPage(pagination.pageIndex + 1);
  };

  return (
    <div className="page-section">
      <div className="space-y-6">
        {/* Page Header */}
        <PageHeader
          title="Delegados"
          description="Lista de delegados profesionales registrados"
          icon={Users}
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
          emptyMessage="No hay delegados registrados"
          emptyDescription="No se encontraron delegados en el sistema."
          emptyIcon={<Users className="h-10 w-10 text-muted-foreground" />}
        />
      </div>
    </div>
  );
}
