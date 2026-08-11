/**
 * Vista para Tarifas Históricas.
 * Ruta: /liquidaciones/finanzas
 *
 * Usa PageHeader + AppDataTable.
 */
"use client";

import { useState } from "react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { Banknote, Calendar as CalendarIcon, DollarSign, Layers, Percent } from "lucide-react";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { useTarifasHistoricas } from "../hooks/useTarifasHistoricas";
import { tipoTarifaSchema } from "../types/finanzas.types";
import type { TarifaHistoricaPeriodo } from "../types/finanzas.types";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

// ── Tipo options (rutas reales del backend) ─────────────────────────────

const TIPO_OPTIONS: { value: string; label: string }[] = [
  { value: "edificaciones", label: "Edificaciones" },
  { value: "habilitacion-urbana", label: "Habilitación Urbana" },
  { value: "mecanica-suelos", label: "Mecánica de Suelos" },
  { value: "impacto-vial", label: "Impacto Vial" },
  { value: "taludes", label: "Taludes" },
  { value: "inspeccion-obra", label: "Inspección de Obra" },
];

// ── Card de Tarifa Historica ─────────────────────────────────────────────

function formatDate(value: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  return isNaN(d.getTime())
    ? value
    : d.toLocaleDateString("es-PE", { year: "numeric", month: "short", day: "numeric" });
}

function TarifaPeriodoCard({ item }: { item: TarifaHistoricaPeriodo }) {
  const tipoLabel = TIPO_OPTIONS.find((o) => o.value === item.tipo_liquidacion)?.label
    ?? item.tipo_liquidacion
    ?? "—";

  return (
    <div className="rounded-2xl border bg-card shadow-sm hover:shadow-lg hover:border-primary/20 transition-all duration-300 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-gradient-to-r from-muted/40 via-muted/20 to-transparent border-b border-border/60 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
            <DollarSign className="h-4 w-4 text-primary" />
          </div>
          <div>
            <p className="text-sm font-bold text-foreground tracking-tight">{tipoLabel}</p>
            <p className="text-[11px] text-muted-foreground">
              {formatDate(item.periodo_inicio)} → {formatDate(item.periodo_fin)}
            </p>
          </div>
        </div>
        {item.tarifa_m2 ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 text-[10px] font-bold text-blue-600 uppercase tracking-wider">
            <Banknote className="h-3 w-3" />
            S/ {Number(item.tarifa_m2.costo_por_m2).toFixed(2)}/m²
          </span>
        ) : null}
      </div>

      {/* Body */}
      <div className="p-4 space-y-3">
        {/* Porcentaje tarifas */}
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
                    {Number(t.porcentaje_liquidacion) * 100}%
                  </span>
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Visitas */}
        {item.tarifas_visitas.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
              Visitas
            </p>
            <div className="flex flex-wrap gap-1.5">
              {item.tarifas_visitas.map((v) => (
                <span
                  key={v.id}
                  className="inline-flex items-center gap-1 rounded-md border border-border/60 bg-muted/20 px-2 py-0.5 text-xs"
                >
                  {v.categoria}
                  <span className="font-bold">{Number(v.porcentaje_uit)} UIT</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {item.tarifas_porcentaje.length === 0 && item.tarifas_visitas.length === 0 && !item.tarifa_m2 && (
          <p className="text-xs text-muted-foreground/60 italic">Sin tarifas en este periodo</p>
        )}
      </div>
    </div>
  );
}

// ── View Component ───────────────────────────────────────────────────────────

export function TarifasView() {
  const [selectedTipo, setSelectedTipo] = useState<string>("edificaciones");
  const [fechaDesde, setFechaDesde] = useState<string>("");
  const [fechaHasta, setFechaHasta] = useState<string>("");

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
    tipo: selectedTipo as (typeof tipoTarifaSchema.options)[number],
    fechaDesde: fechaDesde || undefined,
    fechaHasta: fechaHasta || undefined,
  });

  return (
    <div className="page-section">
      <div className="space-y-6">
        <PageHeader
          title="Tarifario"
          description="Consulta de tarifas históricas por tipo de liquidación"
          icon={DollarSign}
        />

        {/* Filters */}
        <div className="flex flex-wrap items-end gap-4 p-4 bg-muted/20 rounded-xl border border-border/60">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="tipo-select" className="text-xs font-semibold text-muted-foreground">
              Tipo de Liquidación
            </Label>
            <Select value={selectedTipo} onValueChange={setSelectedTipo}>
              <SelectTrigger id="tipo-select" className="w-[220px] h-9">
                <SelectValue placeholder="Seleccionar tipo" />
              </SelectTrigger>
              <SelectContent>
                {TIPO_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Fecha Desde */}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="fecha-desde" className="text-xs font-semibold text-muted-foreground">
              Fecha Desde
            </Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  id="fecha-desde"
                  variant="outline"
                  className="w-[180px] h-9 justify-start text-left font-normal pl-9 relative"
                >
                  <CalendarIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                  {fechaDesde ? (
                    format(new Date(fechaDesde), "PPP", { locale: es })
                  ) : (
                    <span className="text-muted-foreground">Seleccionar...</span>
                  )}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={fechaDesde ? new Date(fechaDesde) : undefined}
                  onSelect={(date) => setFechaDesde(date ? format(date, "yyyy-MM-dd") : "")}
                  locale={es}
                  initialFocus
                  captionLayout="dropdown"
                  startMonth={new Date(new Date().getFullYear() - 100, 0)}
                  endMonth={new Date()}
                />
              </PopoverContent>
            </Popover>
          </div>

          {/* Fecha Hasta */}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="fecha-hasta" className="text-xs font-semibold text-muted-foreground">
              Fecha Hasta
            </Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  id="fecha-hasta"
                  variant="outline"
                  className="w-[180px] h-9 justify-start text-left font-normal pl-9 relative"
                >
                  <CalendarIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                  {fechaHasta ? (
                    format(new Date(fechaHasta), "PPP", { locale: es })
                  ) : (
                    <span className="text-muted-foreground">Seleccionar...</span>
                  )}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={fechaHasta ? new Date(fechaHasta) : undefined}
                  onSelect={(date) => setFechaHasta(date ? format(date, "yyyy-MM-dd") : "")}
                  locale={es}
                  initialFocus
                  captionLayout="dropdown"
                  startMonth={new Date(new Date().getFullYear() - 100, 0)}
                  endMonth={new Date()}
                />
              </PopoverContent>
            </Popover>
          </div>

          {/* Clear filters */}
          {(fechaDesde || fechaHasta) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setFechaDesde("");
                setFechaHasta("");
              }}
              className="h-9 px-3 gap-1 text-xs"
            >
              Limpiar fechas
            </Button>
          )}
        </div>

        {/* Cards */}
        <div className="space-y-4">
          {isLoading ? (
            <div className="flex flex-col gap-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-card rounded-2xl border shadow-sm h-32 animate-pulse" />
              ))}
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center justify-center p-10 text-center border border-dashed border-border rounded-2xl">
              <p className="text-destructive font-medium">Error al cargar las tarifas</p>
              <Button variant="outline" size="sm" className="mt-3" onClick={() => refetch()}>
                Reintentar
              </Button>
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-border rounded-2xl">
              <DollarSign className="h-10 w-10 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No hay periodos tarifarios para los filtros</p>
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-3">
                {items.map((item) => (
                  <TarifaPeriodoCard key={item.id} item={item} />
                ))}
              </div>

              {/* Pagination */}
              {total > pageSize && (
                <div className="flex items-center justify-between gap-4 pt-6 border-t border-border/50">
                  <span className="text-xs text-muted-foreground font-medium">
                    Mostrando {items.length} de {total} periodos
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(page - 1)}
                      disabled={page <= 1}
                      className="h-9 px-4 text-xs font-semibold"
                    >
                      Anterior
                    </Button>
                    <div className="flex items-center gap-1 px-3 h-9 rounded-md bg-muted border border-border">
                      <span className="text-xs font-bold text-foreground">{page}</span>
                      <span className="text-xs text-muted-foreground">de</span>
                      <span className="text-xs font-bold text-foreground">{totalPages}</span>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(page + 1)}
                      disabled={page >= totalPages}
                      className="h-9 px-4 text-xs font-semibold"
                    >
                      Siguiente
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
