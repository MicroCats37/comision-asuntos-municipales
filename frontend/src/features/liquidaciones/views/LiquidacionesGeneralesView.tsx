/**
 * Vista para lista de Liquidaciones Generales (todas las liquidaciones).
 * Ruta: /liquidaciones/generales
 *
 * Usa PageHeader + cards pattern. No AppDataTable.
 * Muestra un listado unificado de todas las liquidaciones.
 */
"use client";

import type { LucideIcon } from "lucide-react";
import { FileText, Plus, Search, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components-app/pages/PageHeader";

const KIND_ICON: LucideIcon = FileText;

export function LiquidacionesGeneralesView() {
  const [searchInput, setSearchInput] = useState("");

  const handleSearch = () => {};
  const handleClearFilter = () => setSearchInput("");
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  };

  return (
    <div className="page-section">
      <div className="space-y-6">
        <PageHeader
          title="Liquidaciones — Generales"
          description="Listado general de todas las liquidaciones"
          icon={KIND_ICON}
          actionNodes={
            <Button className="gap-2 h-11 rounded-xl font-bold shadow-lg shadow-primary/20 shrink-0">
              <Plus className="h-4 w-4" />
              Nueva Liquidación
            </Button>
          }
        />

        <div className="flex items-center gap-4 p-4 bg-muted/20 rounded-xl border border-border/60">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-muted-foreground">
              Filtrar liquidaciones por nombre de proyecto:
            </span>
            <div className="flex items-center gap-2">
              <Input
                placeholder="Ej. Proyecto Ejemplo"
                aria-label="Nombre del proyecto"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={handleKeyDown}
                className="w-[220px] h-9"
              />
              <Button
                variant="default"
                size="sm"
                onClick={handleSearch}
                className="h-9 px-3 gap-1"
              >
                <Search className="h-4 w-4" />
                Buscar
              </Button>
            </div>
          </div>
          {searchInput && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearFilter}
              className="h-8 px-2 gap-1 text-xs"
            >
              <X className="h-3 w-3" />
              Limpiar filtro
            </Button>
          )}
        </div>

        <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-border rounded-xl">
          <KIND_ICON className="h-10 w-10 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">
            Vista general de liquidaciones — en desarrollo
          </p>
        </div>
      </div>
    </div>
  );
}
