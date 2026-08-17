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
import { TarifasFiltroModal } from "../components/TarifasFiltroModal";
import { useTarifasGenerales } from "../hooks/useTarifasGenerales";
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

// Label legible por código de tipo (el backend manda EDIFICACION, HABILITACION_URBANA, etc.)
const TIPO_LABEL: Record<string, string> = {
  EDIFICACION: "Edificaciones",
  HABILITACION_URBANA: "Habilitación Urbana",
  MECANICA_SUELOS: "Mecánica de Suelos",
  IMPACTO_VIAL: "Impacto Vial",
  TALUDES: "Taludes",
  INSPECCION_OBRA: "Inspección de Obra",
  edificaciones: "Edificaciones",
  "habilitacion-urbana": "Habilitación Urbana",
  "mecanica-suelos": "Mecánica de Suelos",
  "impacto-vial": "Impacto Vial",
  taludes: "Taludes",
  "inspeccion-obra": "Inspección de Obra",
};

function TarifaPeriodoCard({ item }: { item: TarifaHistoricaPeriodo }) {
  const tipoLabel =
    TIPO_LABEL[item.tipo_liquidacion] ?? item.tipo_liquidacion ?? "—";

  // Detectar el tipo de motor por la presencia de datos
  const esPorcentaje = item.tarifas_porcentaje.length > 0;
  const esVisitas = item.tarifas_visitas.length > 0;
  const esM2 = !!item.tarifa_m2;

  return (
    <div className="rounded-2xl border bg-card shadow-sm hover:shadow-lg hover:border-primary/20 transition-all duration-300 overflow-hidden">
      {/* Header: tipo + periodo + badge del motor */}
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
        <div className="flex flex-wrap items-center justify-end gap-1.5 shrink-0">
          {esPorcentaje && (
            <span className="inline-flex items-center rounded-full bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 text-[10px] font-bold text-purple-600 uppercase tracking-wider">
              <Percent className="h-3 w-3 mr-1" />
              % Obra
            </span>
          )}
          {esM2 && (
            <span className="inline-flex items-center rounded-full bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 text-[10px] font-bold text-blue-600 uppercase tracking-wider">
              <Banknote className="h-3 w-3 mr-1" />
              Por m²
            </span>
          )}
          {esVisitas && (
            <span className="inline-flex items-center rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-600 uppercase tracking-wider">
              <Building2 className="h-3 w-3 mr-1" />
              Visitas
            </span>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="p-4 space-y-4">
        {/* Especialidades (porcentaje) — una tarjeta por especialidad */}
        {esPorcentaje && (
          <div className="space-y-2">
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
              <Percent className="h-3 w-3 text-primary/60" />
              Especialidades — % de Liquidación
            </p>
            <div className="flex flex-wrap gap-2">
              {item.tarifas_porcentaje.map((t) => (
                <div
                  key={t.id}
                  className="flex-1 min-w-[180px] rounded-xl border border-border/60 bg-muted/20 px-3 py-2 flex items-center justify-between gap-2"
                >
                  <span className="flex items-center gap-1.5 text-xs font-medium truncate">
                    <Layers className="h-3.5 w-3.5 text-primary/60 shrink-0" />
                    {t.especialidad_nombre}
                  </span>
                  <span className="text-xs font-bold text-primary whitespace-nowrap">
                    {formatPorcentaje(t.porcentaje_liquidacion)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Visitas — una tarjeta por categoría */}
        {esVisitas && (
          <div className="space-y-2">
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
              <Building2 className="h-3 w-3 text-primary/60" />
              Categorías de Visitas — % de UIT por visita
            </p>
            <div className="flex flex-wrap gap-2">
              {item.tarifas_visitas.map((v) => (
                <div
                  key={v.id}
                  className="flex-1 min-w-[160px] rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] px-3 py-2 flex items-center justify-between gap-2"
                >
                  <span className="flex items-center gap-2 text-xs font-semibold">
                    <span className="inline-flex h-6 w-6 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/25 text-[11px] font-bold text-emerald-600">
                      {v.categoria}
                    </span>
                    Categoría {v.categoria}
                  </span>
                  <span className="text-xs font-bold text-emerald-700 whitespace-nowrap">
                    {formatPorcentaje(v.porcentaje_uit)} UIT
                  </span>
                </div>
              ))}
            </div>
            <p className="text-[11px] text-muted-foreground/70">
              El costo por visita se calcula como {`porcentaje_uit`} × UIT vigente al momento de liquidar.
            </p>
          </div>
        )}

        {/* M2 — tarjeta con el costo por m² */}
        {esM2 && item.tarifa_m2 && (
          <div className="space-y-2">
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
              <Banknote className="h-3 w-3 text-primary/60" />
              Tarifa por Metro Cuadrado
            </p>
            <div className="rounded-xl border border-blue-500/20 bg-blue-500/[0.04] px-3 py-2.5 flex items-center justify-between gap-2">
              <span className="text-xs font-medium text-muted-foreground">
                Costo por m²
              </span>
              <span className="text-sm font-bold text-blue-600 whitespace-nowrap">
                {formatSoles(item.tarifa_m2.costo_por_m2)}/m²
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground/70">
              Se aplica sobre el área solicitada (m²) de la liquidación.
            </p>
          </div>
        )}

        {/* Sin tarifas */}
        {!esPorcentaje && !esVisitas && !esM2 && (
          <p className="text-xs text-muted-foreground/60 italic">
            Sin tarifas en este periodo
          </p>
        )}
      </div>
    </div>
  );
}

// ── View Component ───────────────────────────────────────────────────────────

export function TarifasView() {
  const [filtros, setFiltros] = useState<TarifasFiltros>({});
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
  } = useTarifasGenerales({
    fechaDesde: filtros.fechaDesde,
    fechaHasta: filtros.fechaHasta,
  });

  const hasFechas = !!filtros.fechaDesde || !!filtros.fechaHasta;
  const activeFilterCount = [filtros.fechaDesde, filtros.fechaHasta].filter(
    Boolean,
  ).length;

  const handleLimpiar = () => {
    setFiltros({});
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
            Todas las liquidaciones
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
                  : "No hay tarifas vigentes"}
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
