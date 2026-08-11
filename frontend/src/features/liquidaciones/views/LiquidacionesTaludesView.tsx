/**
 * Vista para lista de Liquidaciones de Taludes.
 * Ruta: /liquidaciones/taludes
 *
 * Usa PageHeader + cards pattern. No AppDataTable.
 */
"use client";

import { Mountain, Plus, Search, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { LiquidacionTaludesCard } from "../components/cards/LiquidacionTaludesCard";
import { TaludesFormModal } from "../components/forms/TaludesFormModal";
import { useLiquidacionesTaludes } from "../hooks";
import type { LiquidacionTaludesListItem } from "../schemas/liquidacion-taludes.schema";

const KIND_ICON: LucideIcon = Mountain;

export function LiquidacionesTaludesView() {
  const [searchInput, setSearchInput] = useState("");
  const [formModalOpen, setFormModalOpen] = useState(false);

  const {
    items,
    total,
    page,
    pageSize,
    totalPages,
    isLoading,
    isError,
    setPage,
    refetch,
  } = useLiquidacionesTaludes();

  const filteredItems = items.filter((item) =>
    item.liquidacion_general.proyecto.denominacion
      .toLowerCase()
      .includes(searchInput.toLowerCase())
  );

  const handleSearch = () => {};
  const handleClearFilter = () => setSearchInput("");
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  };

  return (
    <div className="page-section">
      <div className="space-y-6">
        <PageHeader
          title="Liquidaciones — Taludes"
          description="Listado de liquidaciones de Taludes"
          icon={KIND_ICON}
          actionNodes={
            <Button
              className="gap-2 h-11 rounded-xl font-bold shadow-lg shadow-primary/20 shrink-0"
              onClick={() => setFormModalOpen(true)}
            >
              <Plus className="h-4 w-4" />
              Nueva Liquidación
            </Button>
          }
        />

        <div className="flex items-center gap-4 p-4 bg-muted/20 rounded-xl border border-border/60">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-muted-foreground">Filtrar liquidaciones por nombre de proyecto:</span>
            <div className="flex items-center gap-2">
              <Input placeholder="Ej. Proyecto Ejemplo" aria-label="Nombre del proyecto" value={searchInput} onChange={(e) => setSearchInput(e.target.value)} onKeyDown={handleKeyDown} className="w-[220px] h-9" />
              <Button variant="default" size="sm" onClick={handleSearch} className="h-9 px-3 gap-1">
                <Search className="h-4 w-4" />
                Buscar
              </Button>
            </div>
          </div>
          {searchInput && (
            <Button variant="ghost" size="sm" onClick={handleClearFilter} className="h-8 px-2 gap-1 text-xs">
              <X className="h-3 w-3" />
              Limpiar filtro
            </Button>
          )}
        </div>

        <div className="space-y-4">
          {isLoading ? (
            <div className="flex flex-col gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-card rounded-xl border shadow-sm h-48 animate-pulse" />
              ))}
            </div>
          ) : isError ? (
            <div className="flex items-center justify-center p-8 text-destructive">Error al cargar las liquidaciones</div>
          ) : filteredItems.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-border rounded-xl">
              <KIND_ICON className="h-10 w-10 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No hay liquidaciones registradas</p>
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-4">
                {filteredItems.map((item) => (
                  <LiquidacionTaludesCard key={item.liquidacion_general.id} item={item as unknown as LiquidacionTaludesListItem} />
                ))}
              </div>
              {total > pageSize && (
                <div className="flex items-center justify-between gap-4 pt-6 border-t border-border/50">
                  <span className="text-xs text-muted-foreground font-medium">Mostrando {filteredItems.length} de {total} liquidaciones</span>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={() => setPage(page - 1)} disabled={page <= 1} className="h-9 px-4 text-xs font-semibold">Anterior</Button>
                    <div className="flex items-center gap-1 px-3 h-9 rounded-md bg-muted border border-border">
                      <span className="text-xs font-bold text-foreground">{page}</span>
                      <span className="text-xs text-muted-foreground">de</span>
                      <span className="text-xs font-bold text-foreground">{totalPages}</span>
                    </div>
                    <Button variant="outline" size="sm" onClick={() => setPage(page + 1)} disabled={page >= totalPages} className="h-9 px-4 text-xs font-semibold">Siguiente</Button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <TaludesFormModal
        open={formModalOpen}
        onOpenChange={setFormModalOpen}
        onSuccess={() => {
          setFormModalOpen(false);
          refetch();
        }}
      />
    </div>
  );
}
