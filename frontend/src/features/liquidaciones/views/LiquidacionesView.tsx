"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { FileText, Plus, LayoutGrid, List } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { AppDataTable } from "@/components-app/tables/AppDataTable";
import { LiquidacionEdificacionFormModal } from "../components/LiquidacionEdificacionFormModal";
import { LiquidacionSnapshotCard } from "../components/LiquidacionSnapshotCard";
import { useLiquidaciones, useLiquidacionesSnapshots } from "../hooks/useLiquidaciones";
import type { LiquidacionListItem } from "../types/liquidacion-edificaciones";

const formatEnumLabel = (value: string | null | undefined): string => {
  if (!value) return "—";
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
};

// ── Column Definitions ────────────────────────────────────────────────────────

const columns: ColumnDef<LiquidacionListItem>[] = [
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => (
      <span className="font-mono text-xs">{row.original.id}</span>
    ),
  },
  {
    accessorKey: "public_id",
    header: "Liquidación",
    cell: ({ row }) => (
      <span className="font-mono text-xs">
        {row.original.public_id || row.original.id}
      </span>
    ),
  },
  {
    accessorKey: "numero_revision",
    header: "Rev.",
    cell: ({ row }) => (
      <span className="font-bold">R{row.original.numero_revision}</span>
    ),
  },
  {
    accessorKey: "proyecto_public_id",
    header: "Proyecto",
    cell: ({ row }) => (
      <div className="space-y-0.5">
        <p className="font-medium text-sm">{row.original.proyecto_public_id}</p>
        <p className="text-xs text-muted-foreground">
          {row.original.proyecto_denominacion}
        </p>
      </div>
    ),
  },
  {
    accessorKey: "tipo_tramite",
    header: "Trámite",
    cell: ({ row }) => (
      <span className="text-sm">
        {formatEnumLabel(row.original.tipo_tramite)}
      </span>
    ),
  },
  {
    accessorKey: "municipalidad_nombre",
    header: "Municipalidad",
    cell: ({ row }) => (
      <span className="text-sm">
        {row.original.municipalidad_nombre || "—"}
      </span>
    ),
  },
  {
    accessorKey: "estado",
    header: "Estado",
    cell: ({ row }) => {
      const estado = row.original.estado;
      const colorClass =
        estado === "PAGADO"
          ? "bg-green-100 text-green-800"
          : estado === "PENDIENTE"
            ? "bg-yellow-100 text-yellow-800"
            : "bg-muted text-muted-foreground";
      return (
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${colorClass}`}
        >
          {estado}
        </span>
      );
    },
  },
  {
    accessorKey: "valor_proyecto",
    header: "Valor Obra",
    cell: ({ row }) => (
      <span className="font-medium">
        S/{" "}
        {row.original.valor_proyecto.toLocaleString("es-PE", {
          minimumFractionDigits: 2,
        })}
      </span>
    ),
  },
  {
    accessorKey: "total",
    header: "Total",
    cell: ({ row }) => (
      <span className="font-bold text-primary">
        S/{" "}
        {row.original.total.toLocaleString("es-PE", {
          minimumFractionDigits: 2,
        })}
      </span>
    ),
  },
  {
    accessorKey: "fecha_registro",
    header: "Fecha",
    cell: ({ row }) => (
      <span className="text-sm text-muted-foreground">
        {row.original.fecha_registro
          ? new Date(row.original.fecha_registro).toLocaleDateString("es-PE")
          : "—"}
      </span>
    ),
  },
];

// ── View Component ────────────────────────────────────────────────────────────

type ViewMode = "table" | "cards";

export function LiquidacionesView() {
  const [formOpen, setFormOpen] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>("table");

  const { items, total, page, pageSize, isLoading, isError, refetch, setPage } =
    useLiquidaciones({ page: 1, pageSize: 10 });

  const {
    items: snapshotItems,
    total: snapshotTotal,
    page: snapshotPage,
    pageSize: snapshotPageSize,
    isLoading: isSnapshotLoading,
    isError: isSnapshotError,
    refetch: refetchSnapshots,
    setPage: setSnapshotPage,
  } = useLiquidacionesSnapshots({ page: 1, pageSize: 10 });

  const handleOpenCreate = () => {
    setFormOpen(true);
  };

  const handleFormSuccess = () => {
    // Refetch the list when a new liquidacion is created
    refetch();
    refetchSnapshots();
  };

  return (
    <div className="page-section">
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-primary/10 rounded-xl border border-primary/20">
              <FileText className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-black tracking-tight">
                Liquidaciones de Edificaciones
              </h1>
              <p className="text-sm text-muted-foreground">
                Gestiona las liquidaciones de proyectos de edificación
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* View Mode Toggle */}
            <div className="flex items-center border border-border rounded-lg overflow-hidden">
              <button
                onClick={() => setViewMode("table")}
                className={`p-2.5 transition-colors ${
                  viewMode === "table"
                    ? "bg-primary text-primary-foreground"
                    : "bg-background hover:bg-muted text-muted-foreground"
                }`}
                title="Vista de tabla"
              >
                <List className="h-4 w-4" />
              </button>
              <button
                onClick={() => setViewMode("cards")}
                className={`p-2.5 transition-colors ${
                  viewMode === "cards"
                    ? "bg-primary text-primary-foreground"
                    : "bg-background hover:bg-muted text-muted-foreground"
                }`}
                title="Vista de tarjetas"
              >
                <LayoutGrid className="h-4 w-4" />
              </button>
            </div>
            <Button
              onClick={handleOpenCreate}
              className="gap-2 h-11 rounded-xl font-bold shadow-lg shadow-primary/20"
            >
              <Plus className="h-4 w-4" />
              Nueva Liquidación
            </Button>
          </div>
        </div>

        {/* Data Views */}
        {viewMode === "table" ? (
          <AppDataTable
            columns={columns}
            data={items}
            isLoading={isLoading}
            isError={isError}
            onRetry={refetch}
            pagination={{ pageIndex: page - 1, pageSize }}
            onPaginationChange={({ pageIndex }) => {
              setPage(pageIndex + 1);
            }}
            showPagination
            rowCount={total}
            emptyMessage="No hay liquidaciones registradas"
            emptyDescription="Usa el botón para crear la primera liquidación"
            emptyIcon={<FileText className="h-10 w-10" />}
            emptyActionLabel="Nueva Liquidación"
            emptyAction={handleOpenCreate}
          />
        ) : (
          /* Cards View */
          <div className="space-y-4">
            {isSnapshotLoading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="bg-card rounded-xl border shadow-sm h-64 animate-pulse"
                  />
                ))}
              </div>
            ) : isSnapshotError ? (
              <div className="flex items-center justify-center p-8 text-destructive">
                Error al cargar las liquidaciones
              </div>
            ) : snapshotItems.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-border rounded-xl">
                <FileText className="h-10 w-10 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No hay liquidaciones registradas</p>
                <Button
                  onClick={handleOpenCreate}
                  className="mt-4 gap-2"
                  variant="outline"
                >
                  <Plus className="h-4 w-4" />
                  Nueva Liquidación
                </Button>
              </div>
            ) : (
              <>
                <div className="flex flex-col gap-4">
                  {snapshotItems.map((item) => (
                    <LiquidacionSnapshotCard key={item.liquidacion_id} item={item} />
                  ))}
                </div>
                {/* Pagination for cards */}
                {snapshotTotal > snapshotPageSize && (
                  <div className="flex items-center justify-between gap-4 pt-6 border-t border-border/50">
                    <span className="text-xs text-muted-foreground font-medium">
                      Mostrando {snapshotItems.length} de {snapshotTotal} liquidaciones
                    </span>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSnapshotPage(snapshotPage - 1)}
                        disabled={snapshotPage <= 1}
                        className="h-9 px-4 text-xs font-semibold"
                      >
                        Anterior
                      </Button>
                      <div className="flex items-center gap-1 px-3 h-9 rounded-md bg-muted border border-border">
                        <span className="text-xs font-bold text-foreground">{snapshotPage}</span>
                        <span className="text-xs text-muted-foreground">de</span>
                        <span className="text-xs font-bold text-foreground">
                          {Math.ceil(snapshotTotal / snapshotPageSize)}
                        </span>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSnapshotPage(snapshotPage + 1)}
                        disabled={snapshotPage >= Math.ceil(snapshotTotal / snapshotPageSize)}
                        className="h-9 px-4 text-xs font-semibold"
                      >
                        Siguiente
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Create Modal */}
        <LiquidacionEdificacionFormModal
          open={formOpen}
          onOpenChange={setFormOpen}
          onSuccess={handleFormSuccess}
        />
      </div>
    </div>
  );
}
