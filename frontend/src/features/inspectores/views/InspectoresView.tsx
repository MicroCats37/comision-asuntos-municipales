"use client";

import { ShieldCheck } from "lucide-react";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { Button } from "@/components/ui/button";
import { useInspectores } from "../hooks/useInspectores";
import { useInspectoresUIStore } from "../store/inspectores-ui.store";
import { InspectorCard } from "../components/InspectorCard";

/**
 * Vista de Inspectores — cards con paginación.
 */
export function InspectoresView() {
  const page = useInspectoresUIStore((s) => s.page);
  const pageSize = useInspectoresUIStore((s) => s.pageSize);
  const setPage = useInspectoresUIStore((s) => s.setPage);

  const {
    items,
    total,
    isLoading,
    isError,
    refetch,
    totalPages,
  } = useInspectores({ page, pageSize });

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
                <div key={i} className="bg-card rounded-2xl border shadow-sm h-24 animate-pulse" />
              ))}
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center justify-center p-10 text-center border border-dashed border-border rounded-2xl">
              <p className="text-destructive font-medium">Error al cargar los inspectores</p>
              <Button variant="outline" size="sm" className="mt-3" onClick={() => refetch()}>
                Reintentar
              </Button>
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-border rounded-2xl">
              <ShieldCheck className="h-10 w-10 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No hay inspectores registrados</p>
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-3">
                {items.map((item) => (
                  <InspectorCard key={item.id} item={item} />
                ))}
              </div>

              {/* Pagination */}
              {total > pageSize && (
                <div className="flex items-center justify-between gap-4 pt-6 border-t border-border/50">
                  <span className="text-xs text-muted-foreground font-medium">
                    Mostrando {items.length} de {total} inspectores
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(page - 1)}
                      disabled={page <= 1}
                      className="h-9 px-4 text-xs font-semibold"
                    >
                      Anterior
                    </Button>
                    <div className="flex items-center gap-1 px-3 h-9 rounded-md bg-muted border border-border">
                      <span className="text-xs font-bold text-foreground">{page}</span>
                      <span className="text-xs text-muted-foreground">de</span>
                      <span className="text-xs font-bold text-foreground">{totalPages}</span>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(page + 1)}
                      disabled={page >= totalPages}
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
      </div>
    </div>
  );
}
