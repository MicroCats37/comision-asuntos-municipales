"use client";

import { HardHat, Search } from "lucide-react";
import { useCallback, useState } from "react";
import { Pagination } from "@/components/genericPagination/Pagination";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useInspectoresAsignaciones } from "@/features/finanzas/hooks/useInspectoresAsignaciones";
import type { LiquidacionInspectorAsignacion } from "@/features/finanzas/schemas/inspector-asignacion.schema";

interface BuscarAsignacionInspectorContentProps {
  onSelect: (asignacion: LiquidacionInspectorAsignacion) => void;
  onCancel?: () => void;
}

export function BuscarAsignacionInspectorContent({
  onSelect,
  onCancel,
}: BuscarAsignacionInspectorContentProps) {
  const [cip, setCip] = useState("");
  const [searched, setSearched] = useState(false);
  const [page, setPage] = useState(1);

  const isCipValid = cip.trim().length >= 3;

  const { items, total, totalPages, pageSize, isLoading, isError, refetch } =
    useInspectoresAsignaciones({
      page,
      pageSize: 10,
      cip: cip || undefined,
      enabled: searched,
    });

  const handleSearch = useCallback(() => {
    if (!isCipValid) return;
    setPage(1);
    setSearched(true);
    refetch();
  }, [isCipValid, refetch]);

  return (
    <div className="space-y-6">
      {/* Búsqueda por CIP */}
      <div className="p-4 rounded-xl border border-border/60 bg-muted/10 space-y-3">
        <div className="space-y-2">
          <Label
            htmlFor="buscar-cip-inspector"
            className="text-sm font-semibold"
          >
            N° CIP del Inspector
          </Label>
          <div className="flex gap-2">
            <Input
              id="buscar-cip-inspector"
              placeholder="Ej. 12345"
              inputMode="numeric"
              value={cip}
              onChange={(e) => {
                const val = e.target.value.replace(/\D/g, "").slice(0, 20);
                setCip(val);
                setSearched(false);
              }}
              onKeyDown={(e) =>
                e.key === "Enter" && isCipValid && handleSearch()
              }
              className="w-full h-10 font-mono"
            />
            <Button
              type="button"
              variant="default"
              onClick={handleSearch}
              disabled={!isCipValid}
              className="h-10 shrink-0 gap-1.5 px-5"
            >
              <Search className="h-4 w-4" />
              Buscar
            </Button>
          </div>
          {cip && !isCipValid && (
            <p className="text-xs text-muted-foreground">
              Ingresa al menos 3 dígitos del CIP
            </p>
          )}
        </div>
      </div>

      {/* Resultados */}
      <div className="border-t border-border/40 pt-5">
        {!searched ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted/40 mb-3">
              <Search className="h-5 w-5 text-muted-foreground/70" />
            </div>
            <p className="text-sm text-muted-foreground">
              Ingresa el número de CIP y presiona Buscar
            </p>
            <p className="text-xs text-muted-foreground/60 mt-1">
              Busca por número de CIP del inspector
            </p>
          </div>
        ) : isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="rounded-xl border bg-card p-4"
                style={{ animationDelay: `${i * 150}ms` }}
              >
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 shrink-0 rounded-lg bg-gradient-to-r from-muted via-muted/50 to-muted animate-pulse" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-2/3 rounded bg-gradient-to-r from-muted via-muted/40 to-muted animate-pulse" />
                    <div className="h-3 w-1/3 rounded bg-gradient-to-r from-muted/70 via-muted/30 to-muted/70 animate-pulse" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <p className="text-destructive font-medium">
              Error al cargar las asignaciones
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
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <HardHat className="h-8 w-8 text-muted-foreground mb-2" />
            <p className="text-muted-foreground text-sm">
              No se encontraron asignaciones para este CIP
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              {items.length} resultado{items.length !== 1 ? "s" : ""}
            </p>
            <div className="flex flex-col gap-2">
              {items.map((item) => {
                const lg = item.liquidacion;
                const insp = item.inspector;
                const esp = item.especialidad_revision;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => onSelect(item)}
                    className="rounded-xl border bg-card p-4 text-left w-full hover:border-primary/40 hover:bg-primary/5 hover:shadow-sm transition-all cursor-pointer"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
                          <HardHat className="h-4 w-4 text-primary" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-semibold truncate">
                            {insp?.nombre_completo ?? "—"}
                          </p>
                          <p className="text-xs text-muted-foreground truncate">
                            CIP: {insp?.cip ?? "—"} · {esp?.nombre ?? "—"}
                          </p>
                        </div>
                      </div>
                      <div className="shrink-0 text-right">
                        <p className="text-xs text-muted-foreground truncate">
                          {lg?.proyecto_denominacion ?? "—"}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {lg?.municipalidad_nombre ?? "—"}
                        </p>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
            {total > pageSize && (
              <div className="pt-2">
                <Pagination
                  currentPage={page}
                  totalPages={totalPages}
                  totalItems={total}
                  pageSize={pageSize}
                  onPageChange={setPage}
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
