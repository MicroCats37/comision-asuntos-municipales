/**
 * Vista para Tarifas (Tarifario).
 * Ruta: /liquidaciones/finanzas
 *
 * Usa PageHeader + cards pattern + filtros en modal.
 * - Sin fechas → el backend devuelve todas las tarifas registradas.
 * - Con fechas (desde/hasta) → filtra por rango.
 */
"use client";

import { parse } from "date-fns";
import {
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
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { TarifasFiltroModal } from "../components/TarifasFiltroModal";
import { useTarifasGenerales } from "../hooks/useTarifasGenerales";
import type {
  TarifaGeneralItem,
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

type TarifaPeriodoGroup = {
  tipo_liquidacion: string;
  periodo_inicio: string;
  periodo_fin: string | null;
  items: TarifaGeneralItem[];
};

function TarifaPeriodoCard({ group }: { group: TarifaPeriodoGroup }) {
  const tipoLabel =
    TIPO_LABEL[group.tipo_liquidacion] ?? group.tipo_liquidacion ?? "—";
  const porcentajeItems = group.items.filter(
    (item): item is Extract<TarifaGeneralItem, { tipo_tarifa: "porcentaje" }> =>
      item.tipo_tarifa === "porcentaje",
  );
  const visitasItems = group.items.filter(
    (item): item is Extract<TarifaGeneralItem, { tipo_tarifa: "visitas" }> =>
      item.tipo_tarifa === "visitas",
  );
  const m2Items = group.items.filter(
    (item): item is Extract<TarifaGeneralItem, { tipo_tarifa: "m2" }> =>
      item.tipo_tarifa === "m2",
  );

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
            <div className="flex items-center gap-2 mt-0.5">
              <p className="text-xs font-semibold text-muted-foreground">
                {formatDate(group.periodo_inicio)}{" "}
                <span className="opacity-50 mx-0.5">→</span>{" "}
                {formatDate(group.periodo_fin)}
              </p>
              {!group.periodo_fin ? (
                <span className="inline-flex items-center rounded-sm bg-green-500/15 px-1.5 py-0.5 text-[9px] font-bold text-green-700 uppercase tracking-wider">
                  Vigente
                </span>
              ) : (
                <span className="inline-flex items-center rounded-sm bg-muted border border-border px-1.5 py-0.5 text-[9px] font-bold text-muted-foreground uppercase tracking-wider">
                  Histórica
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-1.5 shrink-0">
          {porcentajeItems.length > 0 && (
            <span className="inline-flex items-center rounded-full bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 text-[10px] font-bold text-purple-600 uppercase tracking-wider">
              <Percent className="h-3 w-3 mr-1" />
              Obra
            </span>
          )}
          {m2Items.length > 0 && (
            <span className="inline-flex items-center rounded-full bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 text-[10px] font-bold text-blue-600 uppercase tracking-wider">
              <Banknote className="h-3 w-3 mr-1" />
              Por m²
            </span>
          )}
          {visitasItems.length > 0 && (
            <span className="inline-flex items-center rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-600 uppercase tracking-wider">
              <Building2 className="h-3 w-3 mr-1" />
              Visitas
            </span>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="p-4 space-y-4">
        {/* Porcentaje */}
        {porcentajeItems.length > 0 && (
          <div className="space-y-2">
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
              <Percent className="h-3 w-3 text-primary/60" />
              Especialidades — % de Liquidación
            </p>
            <div className="flex flex-col gap-2">
              {porcentajeItems.map((item) => (
                <div
                  key={item.tarifa_porcentaje.id}
                  className="w-full rounded-xl border border-border/60 bg-muted/20 px-3 py-2 flex items-center justify-between gap-2"
                >
                  <span className="flex items-center gap-1.5 text-xs font-medium truncate">
                    <Layers className="h-3.5 w-3.5 text-primary/60 shrink-0" />
                    {item.tarifa_porcentaje.especialidad}
                  </span>
                  <span className="text-xs font-bold text-primary whitespace-nowrap">
                    {formatPorcentaje(item.tarifa_porcentaje.porcentaje)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Visitas */}
        {visitasItems.length > 0 && (
          <div className="space-y-2">
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
              <Building2 className="h-3 w-3 text-primary/60" />
              Categorías de Visitas — % de UIT por visita
            </p>
            <div className="flex flex-col gap-2">
              {visitasItems.map((item) => (
                <div
                  key={item.tarifa_visitas.id}
                  className="w-full rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] px-3 py-2 flex items-center justify-between gap-2"
                >
                  <span className="flex items-center gap-2 text-xs font-semibold">
                    <span className="inline-flex h-6 w-6 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/25 text-[11px] font-bold text-emerald-600">
                      {item.tarifa_visitas.categoria}
                    </span>
                    Categoría {item.tarifa_visitas.categoria}
                  </span>
                  <span className="text-xs font-bold text-emerald-700 whitespace-nowrap">
                    {formatPorcentaje(item.tarifa_visitas.porcentaje_uit)} UIT
                  </span>
                </div>
              ))}
            </div>
            <p className="text-[11px] text-muted-foreground/70">
              El costo por visita se calcula como porcentaje_uit × UIT vigente
              al momento de liquidar.
            </p>
          </div>
        )}

        {/* M2 */}
        {m2Items.map((item) => (
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
                {formatSoles(item.tarifa_m2.monto)}/m²
              </span>
            </div>
            <p className="text-[11px] text-muted-foreground/70">
              Se aplica sobre el área solicitada (m²) de la liquidación.
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function getTarifaPeriodoGroupKey(group: TarifaPeriodoGroup): string {
  return `${group.tipo_liquidacion}-${group.periodo_inicio}-${group.periodo_fin ?? "vigente"}`;
}

function groupTarifasByTipoAndPeriodo(items: TarifaGeneralItem[]) {
  return items.reduce<Record<string, TarifaPeriodoGroup[]>>((groups, item) => {
    const key = item.tipo_liquidacion;
    groups[key] = groups[key] ?? [];
    const groupKey = `${item.periodo_inicio}-${item.periodo_fin ?? "vigente"}`;
    let periodGroup = groups[key].find(
      (group) =>
        `${group.periodo_inicio}-${group.periodo_fin ?? "vigente"}` ===
        groupKey,
    );
    if (!periodGroup) {
      periodGroup = {
        tipo_liquidacion: item.tipo_liquidacion,
        periodo_inicio: item.periodo_inicio,
        periodo_fin: item.periodo_fin,
        items: [],
      };
      groups[key].push(periodGroup);
    }
    periodGroup.items.push(item);
    return groups;
  }, {});
}

// ── View Component ───────────────────────────────────────────────────────────

export function TarifasView() {
  const [filtros, setFiltros] = useState<TarifasFiltros>({});
  const [filtroModalOpen, setFiltroModalOpen] = useState(false);
  const hasFechas = !!filtros.fechaDesde || !!filtros.fechaHasta;
  const hasVigentes = filtros.vigentes ?? false;

  const { items, isLoading, isError, refetch } = useTarifasGenerales({
    vigentes: filtros.vigentes ?? false,
    fechaDesde: filtros.fechaDesde,
    fechaHasta: filtros.fechaHasta,
  });

  const activeFilterCount = [filtros.fechaDesde, filtros.fechaHasta].filter(
    Boolean,
  ).length;
  const groupedItems = groupTarifasByTipoAndPeriodo(items);

  const handleLimpiar = () => {
    setFiltros({});
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

        {(hasVigentes || hasFechas) && (
          <div className="flex flex-wrap items-center gap-2 p-3 bg-muted/20 rounded-xl border border-border/60">
            <span className="text-xs font-semibold text-muted-foreground">
              Filtros activos:
            </span>
            <>
              {hasVigentes && (
                <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                  <CalendarIcon className="h-3 w-3" />
                  Vigentes
                </span>
              )}
              {!hasVigentes && hasFechas && (
                <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-medium">
                  <CalendarIcon className="h-3 w-3" />
                  Histórico por rango
                </span>
              )}
              {!hasVigentes && filtros.fechaDesde && (
                <span className="inline-flex items-center gap-1 rounded-full bg-muted border border-border px-2.5 py-1 text-xs font-medium">
                  Desde: {formatDate(filtros.fechaDesde)}
                </span>
              )}
              {!hasVigentes && filtros.fechaHasta && (
                <span className="inline-flex items-center gap-1 rounded-full bg-muted border border-border px-2.5 py-1 text-xs font-medium">
                  Hasta: {formatDate(filtros.fechaHasta)}
                </span>
              )}
            </>
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
        )}

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
                  : "No hay tarifas registradas"}
              </p>
            </div>
          ) : (
            <>
              <div className="space-y-6">
                {Object.entries(groupedItems).map(
                  ([tipoLiquidacion, periodos]) => (
                    <section key={tipoLiquidacion} className="space-y-3">
                      <div className="flex items-center justify-between gap-3 border-b border-border/70 pb-2">
                        <div>
                          <p className="text-sm font-bold text-foreground">
                            {TIPO_LABEL[tipoLiquidacion] ?? tipoLiquidacion}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {periodos.reduce(
                              (total, periodo) => total + periodo.items.length,
                              0,
                            )}{" "}
                            tarifa
                            {periodos.reduce(
                              (total, periodo) => total + periodo.items.length,
                              0,
                            ) === 1
                              ? ""
                              : "s"}
                          </p>
                        </div>
                      </div>
                      <div
                        className={
                          periodos.length === 1
                            ? "grid grid-cols-1 gap-3"
                            : "grid grid-cols-1 xl:grid-cols-2 gap-3"
                        }
                      >
                        {periodos.map((periodo) => (
                          <TarifaPeriodoCard
                            key={getTarifaPeriodoGroupKey(periodo)}
                            group={periodo}
                          />
                        ))}
                      </div>
                    </section>
                  ),
                )}
              </div>
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
          setFiltroModalOpen(false);
        }}
      />
    </div>
  );
}
