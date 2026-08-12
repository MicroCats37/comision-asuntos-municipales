"use client";

/**
 * SeleccionarUltimaRevisionModal — Modal para seleccionar la liquidación previa
 * (última revisión por proyecto) antes de crear una NUEVA REVISIÓN.
 *
 * Endpoint: GET /liquidaciones/edificaciones/ultima-revision
 * Devuelve lista paginada de la última revisión por proyecto.
 */
import { useCallback, useState } from "react";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Search, Building2, FileText, RefreshCw } from "lucide-react";
import { useUltimaRevisionEdificaciones } from "../../hooks/useUltimaRevisionEdificaciones";
import { Pagination } from "@/components/genericPagination/Pagination";

interface SeleccionarUltimaRevisionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Callback con el ID de la liquidación previa seleccionada */
  onSelect: (liquidacionPreviaId: string) => void;
}

export function SeleccionarUltimaRevisionModal({
  open,
  onOpenChange,
  onSelect,
}: SeleccionarUltimaRevisionModalProps) {
  const [documento, setDocumento] = useState("");
  const [page, setPage] = useState(1);

  const { items, total, totalPages, pageSize, isLoading, isError, refetch } = useUltimaRevisionEdificaciones({
    page,
    pageSize: 10,
    numeroDocumento: documento || undefined,
  });

  const handleSearch = useCallback(() => {
    setPage(1);
    refetch();
  }, [refetch]);

  return (
    <AppFormModal
      open={open}
      onOpenChange={onOpenChange}
      title="Nueva Revisión"
      description="Selecciona la liquidación (última revisión) sobre la que crearás la nueva revisión"
      eyebrow="Edificaciones"
      icon={<RefreshCw className="h-5 w-5 text-primary" />}
      primaryLabel="Seleccionar"
      primaryLoading={false}
      primaryDisabled={true}
      onPrimary={() => undefined}
      schema={undefined as never}
      onSubmit={async () => undefined}
      size="lg"
      preventClose={false}
    >
      {() => (
        <div className="space-y-4">
          {/* Búsqueda por documento */}
          <div className="space-y-2">
            <Label htmlFor="buscar-documento">Número de documento (RUC/DNI)</Label>
            <div className="flex gap-2">
              <Input
                id="buscar-documento"
                placeholder="Ej. 20456789012"
                value={documento}
                onChange={(e) => setDocumento(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                className="w-full"
              />
              <Button type="button" variant="default" onClick={handleSearch} className="shrink-0 gap-1">
                <Search className="h-4 w-4" />
                Buscar
              </Button>
            </div>
          </div>

          {/* Lista de últimas revisiones */}
          <div className="space-y-2">
            {isLoading ? (
              <div className="flex flex-col gap-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="bg-card rounded-xl border h-20 animate-pulse" />
                ))}
              </div>
            ) : isError ? (
              <div className="flex flex-col items-center justify-center p-8 text-center border border-dashed border-border rounded-xl">
                <p className="text-destructive font-medium">Error al cargar las revisiones</p>
                <Button variant="outline" size="sm" className="mt-3" onClick={() => refetch()}>
                  Reintentar
                </Button>
              </div>
            ) : items.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-8 text-center border border-dashed border-border rounded-xl">
                <FileText className="h-8 w-8 text-muted-foreground mb-2" />
                <p className="text-muted-foreground text-sm">No hay liquidaciones previas</p>
              </div>
            ) : (
              <>
                <div className="flex flex-col gap-2">
                  {items.map((item) => {
                    const lg = item.liquidacion_general;
                    return (
                      <button
                        key={lg.id}
                        type="button"
                        onClick={() => onSelect(lg.id)}
                        className="rounded-xl border bg-card p-3 text-left w-full hover:border-primary/40 hover:bg-primary/5 transition-colors cursor-pointer"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
                              <Building2 className="h-4 w-4 text-primary" />
                            </div>
                            <div className="min-w-0">
                              <p className="text-sm font-semibold truncate">{lg.proyecto.denominacion}</p>
                              <p className="text-xs text-muted-foreground truncate">
                                Rev. {lg.numero_revision} · {lg.expediente}
                              </p>
                            </div>
                          </div>
                          <span className="shrink-0 text-xs text-muted-foreground">
                            {lg.municipalidad?.nombre ?? "—"}
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
                {total > pageSize && (
                  <Pagination
                    currentPage={page}
                    totalPages={totalPages}
                    totalItems={total}
                    pageSize={pageSize}
                    onPageChange={setPage}
                  />
                )}
              </>
            )}
          </div>
        </div>
      )}
    </AppFormModal>
  );
}
