"use client";

import { Building2, FileText, FolderOpen, MapPin } from "lucide-react";
import { Pagination } from "@/components/genericPagination/Pagination";
import { Badge } from "@/components/ui/badge";
import { useProyectos } from "../hooks/useProyectos";
import type { ProyectoListItem } from "../types/proyecto";

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatSoles(value: number): string {
  return `S/ ${value.toFixed(2)}`;
}

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString("es-PE", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

// ── Loading Skeleton ─────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="rounded-xl border border-border bg-card p-5 space-y-3 animate-pulse"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3 flex-1">
              <div className="h-10 w-10 rounded-lg bg-muted" />
              <div className="space-y-2 flex-1">
                <div className="h-4 w-48 bg-muted rounded" />
                <div className="h-3 w-32 bg-muted rounded" />
              </div>
            </div>
            <div className="h-5 w-20 bg-muted rounded-full" />
          </div>
          <div className="pl-[46px] flex items-center gap-4">
            <div className="h-3 w-24 bg-muted rounded" />
            <div className="h-3 w-32 bg-muted rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Empty State ─────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-border rounded-xl">
      <FolderOpen className="h-10 w-10 text-muted-foreground mb-4" />
      <p className="text-muted-foreground">No hay proyectos registrados</p>
      <p className="text-xs text-muted-foreground mt-2">
        Los proyectos aparecerán aquí una vez creados
      </p>
    </div>
  );
}

// ── Error State ──────────────────────────────────────────────────────────────

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-destructive/30 rounded-xl">
      <p className="text-destructive font-medium">
        Error al cargar los proyectos
      </p>
      <button
        onClick={onRetry}
        className="mt-3 text-sm text-primary hover:underline"
      >
        Reintentar
      </button>
    </div>
  );
}

// ── Proyecto Row ─────────────────────────────────────────────────────────────

interface ProyectoRowProps {
  proyecto: ProyectoListItem;
}

function ProyectoRow({ proyecto }: ProyectoRowProps) {
  const { entidad, liquidaciones } = proyecto;
  const edificaciones = liquidaciones?.edificaciones ?? [];
  const totalEdificaciones = edificaciones.length;

  // Aggregate totals from edificaciones
  const totalMonto = edificaciones.reduce(
    (sum, ed) => sum + (ed.total ?? 0),
    0,
  );

  return (
    <div className="rounded-xl border border-border bg-card p-5 space-y-3 hover:border-primary/30 transition-colors">
      {/* Header row */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* Icon */}
          <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-primary/10 text-primary shrink-0">
            <Building2 className="h-5 w-5" />
          </div>

          {/* Title + meta */}
          <div className="min-w-0 flex-1">
            <h3 className="font-semibold text-foreground truncate">
              {proyecto.denominacion ?? "Sin denominación"}
            </h3>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-xs text-muted-foreground font-mono">
                {proyecto.public_id}
              </span>
              {proyecto.distrito && (
                <>
                  <span className="text-muted-foreground/30">•</span>
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <MapPin className="h-3 w-3" />
                    {proyecto.distrito}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Badge */}
        <Badge variant="secondary" className="shrink-0">
          {totalEdificaciones}{" "}
          {totalEdificaciones === 1 ? "edificación" : "edificaciones"}
        </Badge>
      </div>

      {/* Address */}
      {proyecto.direccion && (
        <div className="pl-[46px]">
          <p className="text-sm text-muted-foreground truncate">
            {proyecto.direccion}
          </p>
        </div>
      )}

      {/* Entity + Stats row */}
      <div className="pl-[46px] flex flex-wrap items-center gap-x-6 gap-y-2">
        {/* Entidad */}
        {entidad?.nombre && (
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted-foreground">Entidad:</span>
            <span className="text-xs font-medium text-foreground">
              {entidad.nombre}
            </span>
            {entidad.numero_documento && (
              <span className="text-xs text-muted-foreground font-mono">
                ({entidad.tipo_documento}: {entidad.numero_documento})
              </span>
            )}
          </div>
        )}

        {/* Total monto */}
        {totalMonto > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted-foreground">Total:</span>
            <span className="text-xs font-semibold text-primary">
              {formatSoles(totalMonto)}
            </span>
          </div>
        )}
      </div>

      {/* Edificaciones list */}
      {edificaciones.length > 0 && (
        <div className="pl-[46px] space-y-2 mt-2">
          <div className="flex items-center gap-2">
            <FileText className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Liquidaciones
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {edificaciones.map((ed) => (
              <div
                key={ed.id}
                className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-muted/50 border border-border text-xs"
              >
                <span className="font-mono text-muted-foreground">
                  {ed.public_id}
                </span>
                <span className="text-muted-foreground">•</span>
                <span className="text-muted-foreground">
                  Rev. {ed.numero_revision}
                </span>
                <span className="text-muted-foreground">•</span>
                <Badge variant="outline" className="text-[10px] h-4 px-1">
                  {ed.estado}
                </Badge>
                <span className="text-muted-foreground">•</span>
                <span className="font-medium text-foreground">
                  {formatSoles(ed.total)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main View ─────────────────────────────────────────────────────────────────

export function ProyectosView() {
  const {
    items: proyectos,
    total,
    page,
    pageSize,
    totalPages,
    isLoading,
    isError,
    refetch,
    setPage,
    setPageSize,
  } = useProyectos({ page: 1, pageSize: 10 });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-primary/10 rounded-xl border border-primary/20">
            <FolderOpen className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-black tracking-tight">Proyectos</h1>
            <p className="text-sm text-muted-foreground">
              Gestiona los proyectos de liquidaciones
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <LoadingSkeleton />
      ) : isError ? (
        <ErrorState onRetry={refetch} />
      ) : proyectos.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          <div className="space-y-4">
            {proyectos.map((proyecto) => (
              <ProyectoRow key={proyecto.id} proyecto={proyecto} />
            ))}
          </div>

          {/* Pagination */}
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            totalItems={total}
            pageSize={pageSize}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
          />
        </>
      )}
    </div>
  );
}
