/**
 * Vista para lista de Liquidaciones de Inspección de Obra.
 * Ruta: /liquidaciones/inspeccion-obra
 *
 * Usa PageHeader + cards pattern + filtros.
 */
"use client";

import type { LucideIcon } from "lucide-react";
import { ClipboardCheck, Filter, Plus, RefreshCw, X } from "lucide-react";
import { useState } from "react";
import { Pagination } from "@/components/genericPagination/Pagination";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { LiquidacionInspeccionObraCard } from "../components/cards/LiquidacionInspeccionObraCard";
import { ConsultarIngenieroButton } from "../components/forms/ConsultarIngenieroButton";
import { LiquidacionFiltroModal } from "../components/forms/LiquidacionFiltroModal";
import { NuevaRevisionInspeccionObraFormModal } from "../components/forms/NuevaRevisionInspeccionObraFormModal";
import { SeleccionarPreviaModal } from "../components/forms/SeleccionarPreviaModal";
import {
  type LiquidacionFiltros,
  useLiquidacionesInspeccionObra,
} from "../hooks";
import type { LiquidacionGeneralItem } from "../hooks/useLiquidacionesGenerales";

const KIND_ICON: LucideIcon = ClipboardCheck;

export function LiquidacionesInspeccionObraView() {
  const [filtros, setFiltros] = useState<LiquidacionFiltros>({});
  const [filtroModalOpen, setFiltroModalOpen] = useState(false);
  const [selectPreviaOpen, setSelectPreviaOpen] = useState(false);
  const [nuevaRevisionOpen, setNuevaRevisionOpen] = useState(false);
  const [previa, setPrevia] = useState<LiquidacionGeneralItem | null>(null);

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
  } = useLiquidacionesInspeccionObra(filtros);

  const activeFilterCount = Object.values(filtros).filter(Boolean).length;

  return (
    <div className="page-section">
      <div className="space-y-6">
        <PageHeader
          title="Liquidaciones — Inspección de Obra"
          description="Listado de liquidaciones de Inspección de Obra"
          icon={KIND_ICON}
          actionNodes={
            <>
              <Button
                className="gap-2 h-11 rounded-xl font-bold shadow-lg shadow-primary/20 shrink-0"
                onClick={() => setSelectPreviaOpen(true)}
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
                  <LiquidacionInspeccionObraCard
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

      {/* Seleccionar liquidación previa (Edificación o HU) para la primera liquidación IO */}
      <SeleccionarPreviaModal
        open={selectPreviaOpen}
        onOpenChange={setSelectPreviaOpen}
        tiposPermitidos={["EDIFICACION", "HABILITACION_URBANA"]}
        title="Nueva Liquidación"
        description="Busca la liquidación previa (Edificación o Habilitación Urbana) para crear la primera liquidación de Inspección de Obra"
        onSelect={(p) => {
          setPrevia(p);
          setSelectPreviaOpen(false);
          setNuevaRevisionOpen(true);
        }}
      />

      {/* Form liviano de nueva revisión IO */}
      <NuevaRevisionInspeccionObraFormModal
        open={nuevaRevisionOpen}
        onOpenChange={setNuevaRevisionOpen}
        previa={previa}
        onSuccess={() => {
          setNuevaRevisionOpen(false);
          setPrevia(null);
          refetch();
        }}
      />
    </div>
  );
}
