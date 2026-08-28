"use client";

import { Filter, Users, X } from "lucide-react";
import { useState } from "react";
import { Pagination } from "@/components/genericPagination/Pagination";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { DelegadoCard } from "../components/DelegadoCard";
import { DelegadosFiltroModal } from "../components/DelegadosFiltroModal";
import { useDelegados } from "../hooks/useDelegados";
import { useDelegadosUIStore } from "../store/delegados-ui.store";
import type { DelegadoFiltros } from "../types/delegados.types";

/**
 * Vista de Delegados — cards con paginación + filtros.
 * Los filtros activos se muestran arriba de la lista.
 */
export function DelegadosView() {
  const page = useDelegadosUIStore((s) => s.page);
  const pageSize = useDelegadosUIStore((s) => s.pageSize);
  const setPage = useDelegadosUIStore((s) => s.setPage);
  const setPageSize = useDelegadosUIStore((s) => s.setPageSize);

  const [filtros, setFiltros] = useState<DelegadoFiltros>({});
  const [filtroModalOpen, setFiltroModalOpen] = useState(false);

  const { items, total, isLoading, isError, refetch, totalPages } =
    useDelegados({ page, pageSize, filtros });

  const activeFilterCount = Object.values(filtros).filter(Boolean).length;

  const handleClearFiltros = () => {
    setFiltros({});
    setPage(1);
  };

  return (
    <div className="page-section">
      <div className="space-y-6">
        <PageHeader
          title="Delegados"
          description="Lista de delegados profesionales registrados"
          icon={Users}
          actionNodes={
            <Button
              variant={activeFilterCount > 0 ? "default" : "outline"}
              className="gap-2 h-10 rounded-xl font-semibold"
              onClick={() => setFiltroModalOpen(true)}
            >
              <Filter className="h-4 w-4" />
              Filtros
              {activeFilterCount > 0 && (
                <span className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-primary-foreground/20 text-xs font-bold">
                  {activeFilterCount}
                </span>
              )}
            </Button>
          }
        />

        {/* Filtros activos */}
        {activeFilterCount > 0 && (
          <div className="flex flex-wrap items-center gap-2 p-3 bg-muted/20 rounded-xl border border-border/60">
            <span className="text-xs font-semibold text-muted-foreground">
              Filtros activos:
            </span>
            {filtros.cip && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                CIP: {filtros.cip}
              </span>
            )}
            {filtros.municipalidad_id && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                Municipalidad seleccionada
              </span>
            )}
            {filtros.estado && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                Estado: {filtros.estado}
              </span>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearFiltros}
              className="h-7 px-2 gap-1 text-xs text-destructive"
            >
              <X className="h-3 w-3" />
              Limpiar
            </Button>
          </div>
        )}

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
                Error al cargar los delegados
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
              <Users className="h-10 w-10 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                No hay delegados registrados
              </p>
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-3">
                {items.map((item) => (
                  <DelegadoCard key={item.id} item={item} />
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

      {/* Filtro modal — sibling, no nested form */}
      <DelegadosFiltroModal
        open={filtroModalOpen}
        onOpenChange={setFiltroModalOpen}
        initialFiltros={filtros}
        onApply={(nuevos) => {
          setFiltros(nuevos);
          setPage(1);
          setFiltroModalOpen(false);
        }}
      />
    </div>
  );
}
