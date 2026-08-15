/**
 * Vista para Tarifas (Tarifario).
 * Ruta: /liquidaciones/finanzas
 *
 * Usa PageHeader + cards pattern + filtros en modal + paginación.
 * - Sin fechas → el backend devuelve SOLO tarifas VIGENTES (1 periodo).
 * - Con fechas (desde/hasta) → histórico por rango.
 */
"use client";

import { parse } from "date-fns";
import {
  BadgeCheck,
  Banknote,
  Building2,
  Calendar as CalendarIcon,
  DollarSign,
  Filter,
  Layers,
  Percent,
  X,
} from "lucide-react";
import { useState } from "react";
import { Pagination } from "@/components/genericPagination/Pagination";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components-app/pages/PageHeader";
import {
  TarifasFiltroModal,
  TIPO_OPTIONS,
} from "../components/TarifasFiltroModal";
import { useTarifasHistoricas } from "../hooks/useTarifasHistoricas";
import type {
  TarifaHistoricaPeriodo,
  TarifasFiltros,
} from "../types/finanzas.types";

// ── Format helpers ──────────────────────────────────────────────────────

const formatSoles = (value: number | undefined | null): string =>
  value == null
    ? "—"
    : `S/ ${Number(value).toLocaleString("es-PE", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })}`;

// Backend devuelve `porcentaje_liquidacion`/`porcentaje_uit` como fracción
// (ej. 0.0015 → "0.15%").
const formatPorcentaje = (value: number | undefined | null): string => {
  if (value == null) return "—";
  const pct = Number(value) * 100;
  return `${pct.toLocaleString("es-PE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  })}%`;
};

function formatDate(value: string | null): string {
  if (!value) return "—";
  let d: Date;
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    // Fecha "yyyy-MM-dd" → parsear local para evitar el shift de zona horaria
    d = parse(value, "yyyy-MM-dd", new Date());
  } else {
    d = new Date(value);
  }
  return Number.isNaN(d.getTime())
    ? value
    : d.toLocaleDateString("es-PE", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
}

// ── Card de Tarifa ───────────────────────────────────────────────────────

function TarifaPeriodoCard({ item }: { item: TarifaHistoricaPeriodo }) {
  const tipoLabel =
    TIPO_OPTIONS.find((o) => o.value === item.tipo_liquidacion)?.label ??
    item.tipo_liquidacion ??
    "—";

  return (
    <div className="rounded-2xl border bg-card shadow-sm hover:shadow-lg hover:border-primary/20 transition-all duration-300 overflow-hidden">
      {/* Header: tipo + periodo + badge m2 */}
      <div className="px-4 py-3 bg-gradient-to-r from-muted/40 via-muted/20 to-transparent border-b border-border/60 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
            <DollarSign className="h-4 w-4 text-primary" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-bold text-foreground tracking-tight truncate">
              {tipoLabel}
            </p>
            <p className="text-[11px] text-muted-foreground">
              {formatDate(item.periodo_inicio)} → {formatDate(item.periodo_fin)}
            </p>
          </div>
        </div>
        {item.tarifa_m2 && (
          <span className="shrink-0 inline-flex items-center gap-1 rounded-full bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 text-[10px] font-bold text-blue-600 uppercase tracking-wider">
            <Banknote className="h-3 w-3" />
            {formatSoles(item.tarifa_m2.costo_por_m2)}/m²
          </span>
        )}
      </div>

      {/* Body */}
      {(item.tarifas_porcentaje.length > 0 ||
        item.tarifas_visitas.length > 0) && (
        <div className="p-4 space-y-3">
          {/* Especialidades (porcentaje) */}
          {item.tarifas_porcentaje.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                <Percent className="h-3 w-3 text-primary/60" />
                Especialidades
              </p>
              <div className="flex flex-wrap gap-1.5">
                {item.tarifas_porcentaje.map((t) => (
                  <span
                    key={t.id}
                    className="inline-flex items-center gap-1 rounded-md border border-border/60 bg-muted/20 px-2 py-0.5 text-xs"
                  >
                    <Layers className="h-3 w-3 text-primary/60" />
                    {t.especialidad_nombre}
                    <span className="font-bold text-primary">
                      {formatPorcentaje(t.porcentaje_liquidacion)}
                    </span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Visitas */}
          {item.tarifas_visitas.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                <Building2 className="h-3 w-3 text-primary/60" />
                Visitas
              </p>
              <div className="flex flex-wrap gap-1.5">
                {item.tarifas_visitas.map((v) => (
                  <span
                    key={v.id}
                    className="inline-flex items-center gap-1 rounded-md border border-border/60 bg-muted/20 px-2 py-0.5 text-xs"
                  >
                    {v.categoria}
                    <span className="font-bold">
                      {formatPorcentaje(v.porcentaje_uit)} UIT
                    </span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {item.tarifas_porcentaje.length === 0 &&
        item.tarifas_visitas.length === 0 &&
        !item.tarifa_m2 && (
          <div className="p-4">
            <p className="text-xs text-muted-foreground/60 italic">
              Sin tarifas en este periodo
            </p>
          </div>
        )}
    </div>
  );
}

// ── View Component ───────────────────────────────────────────────────────────

export function TarifasView() {
  const [filtros, setFiltros] = useState<TarifasFiltros>({
    tipo: "edificaciones",
  });
  const [filtroModalOpen, setFiltroModalOpen] = useState(false);

  const {
    items,
    total,
    isLoading,
    isError,
    refetch,
    page,
    pageSize,
    totalPages,
    setPage,
    setPageSize,
  } = useTarifasHistoricas({
    tipo: filtros.tipo,
    fechaDesde: filtros.fechaDesde,
    fechaHasta: filtros.fechaHasta,
  });

  const hasFechas = !!filtros.fechaDesde || !!filtros.fechaHasta;
  const activeFilterCount = [filtros.fechaDesde, filtros.fechaHasta].filter(
    Boolean,
  ).length;

  const tipoLabel =
    TIPO_OPTIONS.find((o) => o.value === filtros.tipo)?.label ?? filtros.tipo;

  const handleLimpiar = () => {
    setFiltros({ tipo: "edificaciones" });
    setPage(1);
  };

  return (
    <div className="page-section">
      <div className="space-y-6">
        <PageHeader
          title="Tarifario"
          description="Consulta de tarifas vigentes o históricas por tipo de liquidación"
          icon={DollarSign}
          actionNodes={
            <Button
              variant={activeFilterCount > 0 ? "default" : "outline"}
              className="gap-2 h-11 rounded-xl font-semibold shrink-0"
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
        <div className="flex flex-wrap items-center gap-2 p-3 bg-muted/20 rounded-xl border border-border/60">
          <span className="text-xs font-semibold text-muted-foreground">
            Filtros activos:
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
            Tipo: {tipoLabel}
          </span>
          {hasFechas ? (
            <>
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                <CalendarIcon className="h-3 w-3" />
                Histórico por rango
              </span>
              {filtros.fechaDesde && (
                <span className="inline-flex items-center gap-1 rounded-full bg-muted border border-border px-2.5 py-1 text-xs font-medium">
                  Desde: {formatDate(filtros.fechaDesde)}
                </span>
              )}
              {filtros.fechaHasta && (
                <span className="inline-flex items-center gap-1 rounded-full bg-muted border border-border px-2.5 py-1 text-xs font-medium">
                  Hasta: {formatDate(filtros.fechaHasta)}
                </span>
              )}
            </>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-green-500/10 border border-green-500/20 px-2.5 py-1 text-xs font-medium text-green-600">
              <BadgeCheck className="h-3 w-3" />
              Solo vigentes
            </span>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLimpiar}
            className="h-7 px-2 gap-1 text-xs text-destructive"
          >
            <X className="h-3 w-3" />
            Limpiar
          </Button>
        </div>

        {/* Cards */}
        <div className="space-y-4">
          {isLoading ? (
            <div className="flex flex-col gap-3">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="bg-card rounded-2xl border shadow-sm h-32 animate-pulse"
                />
              ))}
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center justify-center p-10 text-center border border-dashed border-border rounded-2xl">
              <p className="text-destructive font-medium">
                Error al cargar las tarifas
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
              <DollarSign className="h-10 w-10 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                {hasFechas
                  ? "No hay periodos tarifarios en el rango seleccionado"
                  : "No hay tarifas vigentes para el tipo seleccionado"}
              </p>
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-3">
                {items.map((item) => (
                  <TarifaPeriodoCard key={item.id} item={item} />
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
      <TarifasFiltroModal
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
