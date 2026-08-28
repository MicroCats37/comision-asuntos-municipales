"use client";

import { Building2, Hash, Loader2, RefreshCw, Search, X } from "lucide-react";
/**
 * SeleccionarUltimaRevisionModal — Modal para seleccionar la liquidación previa
 * (última revisión por proyecto) antes de crear una NUEVA REVISIÓN.
 *
 * Endpoint: GET /liquidaciones/edificaciones/ultima-revision
 * NO dispara la búsqueda al abrir — espera a que el usuario presione "Buscar".
 * Validación: DNI 8 dígitos, RUC 11 dígitos o N° de liquidación para activar el botón.
 */
import { useCallback, useState } from "react";
import { GenericModal } from "@/components/genericModal/GenericModal";
import { Pagination } from "@/components/genericPagination/Pagination";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useUltimaRevisionEdificaciones } from "../../hooks/useUltimaRevisionEdificaciones";
import { formatPublicId } from "../../utils/formatPublicId";

interface SeleccionarUltimaRevisionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (previa: any) => void;
}

/** Loader suave — shimmer */
function SmoothLoader() {
  return (
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
  );
}

export function SeleccionarUltimaRevisionModal({
  open,
  onOpenChange,
  onSelect,
}: SeleccionarUltimaRevisionModalProps) {
  const [documento, setDocumento] = useState("");
  const [numero, setNumero] = useState("");
  const [searched, setSearched] = useState(false);
  const [page, setPage] = useState(1);

  const isDocumentoValid =
    documento.trim().length === 8 || documento.trim().length === 11;
  const canSearch = isDocumentoValid || numero.trim() !== "";

  const { items, total, totalPages, pageSize, isLoading, isError, refetch } =
    useUltimaRevisionEdificaciones({
      page,
      pageSize: 10,
      numeroDocumento: documento || undefined,
      numero: numero ? Number(numero) : undefined,
      enabled: searched && open,
    });

  const handleSearch = useCallback(() => {
    if (!canSearch) return;
    setPage(1);
    setSearched(true);
    refetch();
  }, [canSearch, refetch]);

  const handleReset = useCallback(() => {
    setDocumento("");
    setNumero("");
    setSearched(false);
    setPage(1);
  }, []);

  return (
    <GenericModal open={open} onOpenChange={onOpenChange} preventClose={false}>
      <GenericModal.Content size="lg">
        <GenericModal.Header
          title=""
          className="bg-primary/[0.03] border-b border-border px-6 py-5"
        >
          <div className="flex items-center gap-3 w-full">
            <div className="p-2 bg-primary/10 rounded-xl border border-primary/20 shadow-sm shrink-0">
              <RefreshCw className="h-5 w-5 text-primary" />
            </div>
            <div className="flex flex-col gap-0.5 min-w-0 flex-1">
              <span className="hidden sm:block text-[10px] font-bold uppercase tracking-widest text-primary leading-none">
                Edificaciones
              </span>
              <h2 className="text-2xl font-black tracking-tight text-foreground leading-tight">
                Nueva Revisión
              </h2>
              <p className="hidden sm:block text-sm text-muted-foreground leading-relaxed">
                Busca la liquidación previa para crear una nueva revisión
              </p>
            </div>
            <div className="w-9 shrink-0" aria-hidden="true" />
          </div>
        </GenericModal.Header>

        <GenericModal.Body className="space-y-6">
          {/* ── Búsqueda (sección separada) ── */}
          <div className="p-4 rounded-xl border border-border/60 bg-muted/10 space-y-3">
            <div className="space-y-2">
              <Label
                htmlFor="buscar-documento"
                className="text-sm font-semibold"
              >
                N° Documento (RUC/DNI)
              </Label>
              <div className="flex gap-2">
                <Input
                  id="buscar-documento"
                  placeholder="Ej. 20456789012"
                  inputMode="numeric"
                  value={documento}
                  onChange={(e) => {
                    const val = e.target.value.replace(/\D/g, "").slice(0, 11);
                    setDocumento(val);
                    setSearched(false);
                  }}
                  onKeyDown={(e) =>
                    e.key === "Enter" && canSearch && handleSearch()
                  }
                  className="w-full h-10 font-mono"
                />
                <Button
                  type="button"
                  variant="default"
                  onClick={handleSearch}
                  disabled={!canSearch}
                  className="h-10 shrink-0 gap-1.5 px-5"
                >
                  <Search className="h-4 w-4" />
                  Buscar
                </Button>
              </div>
              {documento && !isDocumentoValid && !numero.trim() && (
                <p className="text-xs text-destructive">
                  El documento debe tener 8 (DNI) u 11 (RUC) dígitos
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="buscar-numero" className="text-sm font-semibold">
                N° Liquidación
              </Label>
              <div className="relative">
                <Hash className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                <Input
                  id="buscar-numero"
                  placeholder="Ej. 15"
                  inputMode="numeric"
                  value={numero}
                  onChange={(e) => {
                    const val = e.target.value.replace(/\D/g, "").slice(0, 10);
                    setNumero(val);
                    setSearched(false);
                  }}
                  onKeyDown={(e) =>
                    e.key === "Enter" && canSearch && handleSearch()
                  }
                  className="w-full h-10 font-mono pl-9"
                />
              </div>
            </div>
          </div>

          {/* ── Resultados (separados del buscador) ── */}
          <div className="border-t border-border/40 pt-5">
            {!searched ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted/40 mb-3">
                  <Search className="h-5 w-5 text-muted-foreground/70" />
                </div>
                <p className="text-sm text-muted-foreground">
                  Ingresa un documento o N° de liquidación y presiona Buscar
                </p>
                <p className="text-xs text-muted-foreground/60 mt-1">
                  DNI: 8 dígitos · RUC: 11 dígitos · N° Liquidación: correlativo
                </p>
              </div>
            ) : isLoading ? (
              <SmoothLoader />
            ) : isError ? (
              <div className="flex flex-col items-center justify-center py-10 text-center">
                <p className="text-destructive font-medium">
                  Error al cargar las revisiones
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
                <Building2 className="h-8 w-8 text-muted-foreground mb-2" />
                <p className="text-muted-foreground text-sm">
                  No se encontraron liquidaciones previas
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  {total} resultado{total !== 1 ? "s" : ""}
                </p>
                <div className="flex flex-col gap-2">
                  {items.map((item: any) => {
                    const lg = item.liquidacion_general;
                    return (
                      <button
                        key={lg.id}
                        type="button"
                        onClick={() => onSelect(item)}
                        className="rounded-xl border bg-card p-4 text-left w-full hover:border-primary/40 hover:bg-primary/5 hover:shadow-sm transition-all cursor-pointer"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-3 min-w-0">
                            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
                              <Building2 className="h-4 w-4 text-primary" />
                            </div>
                            <div className="min-w-0">
                              <p className="text-sm font-semibold truncate">
                                {lg.proyecto.denominacion}
                              </p>
                              <p className="text-xs text-muted-foreground truncate">
                                {lg.expediente || "Sin expediente"}
                              </p>
                            </div>
                          </div>
                          <div className="flex flex-col items-end gap-1 shrink-0">
                            <span className="inline-flex items-center rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-bold text-primary">
                              Rev. {lg.numero_revision}
                            </span>
                            <span className="text-[11px] font-mono text-muted-foreground">
                              {formatPublicId(
                                "edificacion",
                                lg.fecha_registro,
                                item.liquidacion_especifica.numero,
                              )}
                            </span>
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
        </GenericModal.Body>

        <GenericModal.Footer className="px-6 py-4 bg-muted/30 border-t border-border">
          <div className="flex items-center justify-end gap-2">
            {searched && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleReset}
                className="h-10 gap-1 text-xs text-muted-foreground"
              >
                <X className="h-3 w-3" />
                Limpiar
              </Button>
            )}
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              className="h-10 rounded-xl font-semibold"
            >
              Cancelar
            </Button>
          </div>
        </GenericModal.Footer>

        <GenericModal.CloseX />
      </GenericModal.Content>
    </GenericModal>
  );
}
