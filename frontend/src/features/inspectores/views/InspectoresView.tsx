"use client";

import { ShieldCheck } from "lucide-react";
import { Pagination } from "@/components/genericPagination/Pagination";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { useUrlPagination } from "@/hooks/system/useUrlPagination";
import { InspectorCard } from "../components/InspectorCard";
import { useInspectores } from "../hooks/useInspectores";

/**
 * Vista de Inspectores — cards con paginación URL-driven.
 *
 * Backend solo soporta paginación (page/page_size).
 * No se crean filtros falsos ya que el backend no los soporta.
 */
export function InspectoresView() {
  const { page, pageSize, setPage, setPageSize } = useUrlPagination();

  const { items, total, isLoading, isError, refetch, totalPages } =
    useInspectores({ page, pageSize });

  return (
    <div className="page-section">
      <div className="space-y-6">
        <PageHeader
          title="Inspectores"
          description="Lista de inspectores registrados"
          icon={ShieldCheck}
        />

        {/* Cards */}
        <div className="space-y-4">
          {isLoading ? (
            <div className="flex flex-col gap-3">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="bg-card rounded-2xl border shadow-sm h-24 animate-pulse"
                />
              ))}
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center justify-center p-10 text-center border border-dashed border-border rounded-2xl">
              <p className="text-destructive font-medium">
                Error al cargar los inspectores
              </p>
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={() => refetch()}
              >
                Reintentar
              </Button>
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-border rounded-2xl">
              <ShieldCheck className="h-10 w-10 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                No hay inspectores registrados
              </p>
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-3">
                {items.map((item) => (
                  <InspectorCard key={item.id} item={item} />
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
      </div>
    </div>
  );
}
