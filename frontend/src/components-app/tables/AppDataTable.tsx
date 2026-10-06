"use client";

import {
  type ColumnDef,
  getCoreRowModel,
  getPaginationRowModel,
  type PaginationState,
  useReactTable,
} from "@tanstack/react-table";
import { AlertCircle, Inbox, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

// ── Props ─────────────────────────────────────────────────────────────────────

export interface AppDataTableProps<TData> {
  /** Column definitions using @tanstack/react-table */
  columns: ColumnDef<TData>[];
  /** Row data */
  data: TData[];
  /** Loading state — shows skeleton rows */
  isLoading?: boolean;
  /** Error state — shows error message + retry button */
  isError?: boolean;
  /** Callback to refetch data on error */
  onRetry?: () => void;
  /** Empty state message */
  emptyMessage?: string;
  /** Empty state description */
  emptyDescription?: string;
  /** Empty state icon */
  emptyIcon?: ReactNode;
  /** Empty state CTA label */
  emptyActionLabel?: string;
  /** Empty state CTA callback */
  emptyAction?: () => void;
  /** Pagination state */
  pagination?: PaginationState;
  /** Callback when pagination changes */
  onPaginationChange?: (pagination: PaginationState) => void;
  /** Whether to show pagination controls */
  showPagination?: boolean;
  /** Total row count for pagination */
  rowCount?: number;
  /** Callback for row actions (e.g., approve, reject) — receives (action: string, row: TData) */
  onRowAction?: (action: string, row: TData) => void;
  /** Callback when a row is clicked */
  onRowClick?: (row: TData) => void;
  /** Additional className for the table container */
  className?: string;
}

// ── Skeleton Row ──────────────────────────────────────────────────────────────

function SkeletonRow({ cells }: { cells: number }) {
  return (
    <TableRow className="hover:bg-transparent">
      {Array.from({ length: cells }, (_, i) => (
        <TableCell key={i} className="py-4">
          {i === 0 ? (
            // First cell: avatar placeholder
            <div className="h-10 w-10 rounded-2xl bg-muted animate-pulse" />
          ) : (
            // Subsequent cells: text blocks
            <div className="h-4 w-full rounded-[20px] bg-muted animate-pulse" />
          )}
        </TableCell>
      ))}
    </TableRow>
  );
}

// ── Avatar Cell Helper ─────────────────────────────────────────────────────────

export function getAvatarInitials(nombres: string, apellidos: string): string {
  return `${nombres.charAt(0)}${apellidos.split(" ")[0]?.charAt(0) || ""}`.toUpperCase();
}

// ── Component ─────────────────────────────────────────────────────────────────

export function AppDataTable<TData>({
  columns,
  data,
  isLoading = false,
  isError = false,
  onRetry,
  emptyMessage = "No hay datos para mostrar",
  emptyDescription,
  emptyIcon,
  emptyActionLabel,
  emptyAction,
  pagination,
  onPaginationChange,
  showPagination = true,
  rowCount,
  onRowAction,
  onRowClick,
  className,
}: AppDataTableProps<TData>) {
  const paginationState: PaginationState = pagination ?? {
    pageIndex: 0,
    pageSize: 10,
  };

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: showPagination ? getPaginationRowModel() : undefined,
    state: {
      pagination: showPagination ? paginationState : undefined,
    },
    onPaginationChange: showPagination
      ? (updater) => {
          const next =
            typeof updater === "function" ? updater(paginationState) : updater;
          onPaginationChange?.(next);
        }
      : undefined,
    manualPagination: !showPagination,
    pageCount:
      showPagination && rowCount !== undefined
        ? Math.ceil(rowCount / paginationState.pageSize)
        : undefined,
  });

  const skeletonCellCount = columns.length;

  // Build cells for a row — passes onRowAction down via row.original
  const getRowProps = (
    row: ReturnType<typeof table.getRowModel>["rows"][number],
  ) => {
    // Row-level action handler — cells can call this via row.original.__action
    return {};
  };

  return (
    <div
      className={cn(
        "animate-in fade-in slide-in-from-bottom-4 duration-700",
        className,
      )}
    >
      {/* Outer container — rounded card with decorative background */}
      <div className="relative bg-card rounded-[28px] border border-border/50 shadow-sm overflow-hidden">
        {/* Decorative background blob — purely decorative, behind content */}
        <div
          className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full -mr-32 -mt-32 opacity-30 blur-3xl pointer-events-none transition-transform duration-1000 group-hover:scale-110"
          aria-hidden="true"
        />

        {/* Table container — overflow-x-auto for mobile scroll */}
        <div className="relative z-10 overflow-x-auto">
          <Table>
            <TableHeader>
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow
                  key={headerGroup.id}
                  className="bg-muted/30 border-b border-border"
                >
                  {headerGroup.headers.map((header) => (
                    <TableHead
                      key={header.id}
                      className="text-xs font-bold uppercase tracking-wider text-muted-foreground py-3"
                    >
                      {header.isPlaceholder
                        ? null
                        : typeof header.column.columnDef.header === "function"
                          ? header.column.columnDef.header(header.getContext())
                          : header.column.columnDef.header}
                    </TableHead>
                  ))}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {/* Loading state — skeleton rows */}
              {isLoading && (
                <>
                  {Array.from({ length: 6 }, (_, i) => (
                    <SkeletonRow key={i} cells={skeletonCellCount} />
                  ))}
                </>
              )}

              {/* Error state */}
              {isError && !isLoading && (
                <TableRow className="hover:bg-transparent">
                  <TableCell
                    colSpan={skeletonCellCount}
                    className="h-48 text-center"
                  >
                    <div className="flex flex-col items-center gap-3 animate-in fade-in duration-500">
                      <div className="bg-destructive/10 border border-destructive/20 rounded-2xl p-4">
                        <AlertCircle className="h-8 w-8 text-destructive" />
                      </div>
                      <div className="space-y-1">
                        <p className="text-sm font-medium text-destructive">
                          Error al cargar los datos
                        </p>
                        {emptyDescription && (
                          <p className="text-xs text-muted-foreground">
                            {emptyDescription}
                          </p>
                        )}
                      </div>
                      {onRetry && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={onRetry}
                          className="mt-1 gap-2"
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                          Reintentar
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              )}

              {/* Empty state */}
              {!isLoading &&
                !isError &&
                table.getRowModel().rows.length === 0 && (
                  <TableRow className="hover:bg-transparent">
                    <TableCell
                      colSpan={skeletonCellCount}
                      className="h-48 text-center"
                    >
                      <div className="flex flex-col items-center gap-3 animate-in fade-in duration-500">
                        <div className="bg-muted/30 border border-border/50 rounded-2xl p-4">
                          {emptyIcon ? (
                            <div className="text-muted-foreground">
                              {emptyIcon}
                            </div>
                          ) : (
                            <Inbox className="h-10 w-10 text-muted-foreground" />
                          )}
                        </div>
                        <div className="space-y-1">
                          <p className="text-sm font-medium text-foreground">
                            {emptyMessage}
                          </p>
                          {emptyDescription && (
                            <p className="text-xs text-muted-foreground max-w-xs mx-auto leading-relaxed">
                              {emptyDescription}
                            </p>
                          )}
                        </div>
                        {emptyAction && emptyActionLabel && (
                          <Button
                            size="sm"
                            onClick={emptyAction}
                            className="mt-2 gap-2"
                          >
                            {emptyActionLabel}
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                )}

              {/* Data rows */}
              {!isLoading &&
                !isError &&
                table.getRowModel().rows.map((row) => (
                  <TableRow
                    key={row.id}
                    onClick={
                      onRowClick ? () => onRowClick(row.original) : undefined
                    }
                    className={cn(
                      "hover:bg-muted/30 transition-colors",
                      onRowClick && "cursor-pointer hover:bg-muted/50",
                    )}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id} className="py-4 text-sm">
                        {typeof cell.column.columnDef.cell === "function"
                          ? cell.column.columnDef.cell(cell.getContext())
                          : cell.getValue()}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Pagination */}
      {showPagination && table.getCanNextPage() && (
        <div className="flex items-center justify-between gap-4 px-2">
          <p className="text-sm text-muted-foreground">
            {rowCount !== undefined && (
              <>
                Mostrando{" "}
                <span className="font-medium text-foreground">
                  {paginationState.pageIndex * paginationState.pageSize + 1}
                </span>{" "}
                a{" "}
                <span className="font-medium text-foreground">
                  {Math.min(
                    (paginationState.pageIndex + 1) * paginationState.pageSize,
                    rowCount,
                  )}
                </span>{" "}
                de{" "}
                <span className="font-medium text-foreground">{rowCount}</span>
              </>
            )}
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
              className="h-8 rounded-lg"
            >
              Anterior
            </Button>
            <span className="text-xs font-medium text-foreground px-2">
              Página {paginationState.pageIndex + 1}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
              className="h-8 rounded-lg"
            >
              Siguiente
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
