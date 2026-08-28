/**
 * Vista para lista de Liquidaciones de Habilitación Urbana.
 * Ruta: /liquidaciones/habilitacion-urbana
 *
 * Usa PageHeader + cards pattern + filtros.
 */
"use client";

import type { LucideIcon } from "lucide-react";
import { Filter, Map, Plus, X } from "lucide-react";
import { useState } from "react";
import { Pagination } from "@/components/genericPagination/Pagination";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { LiquidacionHabilitacionUrbanaCard } from "../components/cards/LiquidacionHabilitacionUrbanaCard";
import { ConsultarIngenieroButton } from "../components/forms/ConsultarIngenieroButton";
import { HabilitacionUrbanaFormModal } from "../components/forms/HabilitacionUrbanaFormModal";
import { LiquidacionFiltroModal } from "../components/forms/LiquidacionFiltroModal";
import {
  type LiquidacionFiltros,
  useLiquidacionesHabilitacionUrbana,
} from "../hooks";

const KIND_ICON: LucideIcon = Map;

export function LiquidacionesHabilitacionUrbanaView() {
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [filtros, setFiltros] = useState<LiquidacionFiltros>({});
  const [filtroModalOpen, setFiltroModalOpen] = useState(false);

  const {
    items,
    total,
    page,
    pageSize,
    totalPages,
    isLoading,
    isError,
    setPage,
    setPageSize,
    refetch,
  } = useLiquidacionesHabilitacionUrbana(filtros);

  const activeFilterCount = Object.values(filtros).filter(Boolean).length;

  return (
    <div className="page-section">
      <div className="space-y-6">
        <PageHeader
          title="Liquidaciones — Habilitación Urbana"
          description="Listado de liquidaciones de Habilitación Urbana"
          icon={KIND_ICON}
          actionNodes={
            <>
              <Button
                className="gap-2 h-11 rounded-xl font-bold shadow-lg shadow-primary/20 shrink-0"
                onClick={() => setFormModalOpen(true)}
              >
                <Plus className="h-4 w-4" />
                Nueva Liquidación
              </Button>
              <ConsultarIngenieroButton />
              <Button
                variant={activeFilterCount > 0 ? "default" : "outline"}
                className="gap-2 h-11 rounded-xl font-semibold shrink-0 ml-auto"
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
            </>
          }
        />

        {/* Filtros activos */}
        {activeFilterCount > 0 && (
          <div className="flex flex-wrap items-center gap-2 p-3 bg-muted/20 rounded-xl border border-border/60">
            <span className="text-xs font-semibold text-muted-foreground">
              Filtros activos:
            </span>
            {filtros.propietario && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                Propietario: {filtros.propietario}
              </span>
            )}
            {filtros.razon_social && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                Razón Social: {filtros.razon_social}
              </span>
            )}
            {filtros.entidad_id && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                Municipalidad
              </span>
            )}
            {filtros.fecha_desde && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                Desde: {filtros.fecha_desde}
              </span>
            )}
            {filtros.fecha_hasta && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                Hasta: {filtros.fecha_hasta}
              </span>
            )}
            {filtros.creado_por && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                Creado por: {filtros.creado_por}
              </span>
            )}
            {filtros.numero && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                N°: {filtros.numero}
              </span>
            )}
            {filtros.numero_revisiones && (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                Rev: {filtros.numero_revisiones}
              </span>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setFiltros({});
                setPage(1);
              }}
              className="h-7 px-2 gap-1 text-xs text-destructive"
            >
              <X className="h-3 w-3" />
              Limpiar
            </Button>
          </div>
        )}

        <div className="space-y-4">
          {isLoading ? (
            <div className="flex flex-col gap-4">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="bg-card rounded-xl border shadow-sm h-48 animate-pulse"
                />
              ))}
            </div>
          ) : isError ? (
            <div className="flex items-center justify-center p-8 text-destructive">
              Error al cargar las liquidaciones
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-border rounded-xl">
              <KIND_ICON className="h-10 w-10 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                No hay liquidaciones registradas
              </p>
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-4">
                {items.map((item) => (
                  <LiquidacionHabilitacionUrbanaCard
                    key={item.liquidacion_general.id}
                    item={item}
                  />
                ))}
              </div>
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
      <LiquidacionFiltroModal
        open={filtroModalOpen}
        onOpenChange={setFiltroModalOpen}
        initialFiltros={filtros}
        onApply={(nuevos) => {
          setFiltros(nuevos);
          setPage(1);
          setFiltroModalOpen(false);
        }}
      />

      <HabilitacionUrbanaFormModal
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
