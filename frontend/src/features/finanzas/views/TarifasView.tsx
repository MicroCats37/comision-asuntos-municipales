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
import { DollarSign, Calendar as CalendarIcon } from "lucide-react";
import { type ColumnDef } from "@tanstack/react-table";
import { PageHeader } from "@/components-app/pages/PageHeader";
import { AppDataTable } from "@/components-app/tables/AppDataTable";
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

// ── Tipo options ─────────────────────────────────────────────────────────────

const TIPO_OPTIONS: { value: string; label: string }[] = [
  { value: "edificaciones", label: "Edificaciones" },
  { value: "habilitacion-urbana", label: "Habilitación Urbana" },
  { value: "ms", label: "Mecánica de Suelos" },
  { value: "iv", label: "Impacto Vial" },
  { value: "taludes", label: "Taludes" },
  { value: "io", label: "Inspección de Obra" },
];

// ── Column Definitions ────────────────────────────────────────────────────────

const columns: ColumnDef<TarifaHistoricaPeriodo>[] = [
  {
    accessorKey: "periodo_inicio",
    header: "Periodo Inicio",
    cell: ({ row }) => (
      <span className="font-medium">
        {new Date(row.original.periodo_inicio).toLocaleDateString("es-PE", {
          year: "numeric",
          month: "short",
          day: "numeric",
        })}
      </span>
    ),
  },
  {
    accessorKey: "periodo_fin",
    header: "Periodo Fin",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.periodo_fin
          ? new Date(row.original.periodo_fin).toLocaleDateString("es-PE", {
              year: "numeric",
              month: "short",
              day: "numeric",
            })
          : "—"}
      </span>
    ),
  },
  {
    accessorKey: "tipo_liquidacion",
    header: "Tipo Liquidación",
    cell: ({ row }) => (
      <span className="inline-flex items-center rounded-md bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">
        {row.original.tipo_liquidacion}
      </span>
    ),
  },
  {
    accessorKey: "tarifas_porcentaje",
    header: "Especialidades",
    cell: ({ row }) => (
      <div className="flex flex-col gap-0.5">
        {row.original.tarifas_porcentaje.slice(0, 3).map((t) => (
          <span key={t.id} className="text-xs">
            {t.especialidad_nombre}: {t.porcentaje_liquidacion}%
          </span>
        ))}
        {row.original.tarifas_porcentaje.length > 3 && (
          <span className="text-xs text-muted-foreground">
            +{row.original.tarifas_porcentaje.length - 3} más
          </span>
        )}
      </div>
    ),
  },
  {
    accessorKey: "tarifa_m2",
    header: "Tarifa M²",
    cell: ({ row }) =>
      row.original.tarifa_m2 ? (
        <span className="font-mono text-sm">
          {row.original.tarifa_m2.costo_por_m2.toFixed(2)}
        </span>
      ) : (
        <span className="text-muted-foreground">—</span>
      ),
  },
  {
    accessorKey: "tarifas_visitas",
    header: "Visitas",
    cell: ({ row }) =>
      row.original.tarifas_visitas.length > 0 ? (
        <div className="flex flex-col gap-0.5">
          {row.original.tarifas_visitas.slice(0, 2).map((v) => (
            <span key={v.id} className="text-xs">
              {v.categoria}: {v.porcentaje_uit} UIT
            </span>
          ))}
          {row.original.tarifas_visitas.length > 2 && (
            <span className="text-xs text-muted-foreground">
              +{row.original.tarifas_visitas.length - 2} más
            </span>
          )}
        </div>
      ) : (
        <span className="text-muted-foreground">—</span>
      ),
  },
];

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

  // AppDataTable uses 0-based pageIndex; our hook uses 1-based
  const paginationState = {
    pageIndex: page - 1,
    pageSize,
  };

  const handlePaginationChange = (pagination: { pageIndex: number; pageSize: number }) => {
    setPage(pagination.pageIndex + 1);
  };

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
          {/* Tipo selector */}
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

        {/* Data Table */}
        <AppDataTable
          columns={columns}
          data={items}
          isLoading={isLoading}
          isError={isError}
          onRetry={refetch}
          pagination={paginationState}
          onPaginationChange={handlePaginationChange}
          showPagination={true}
          rowCount={total}
          emptyMessage="No hay periodos tarifarios"
          emptyDescription="No se encontraron tarifas históricas para los filtros seleccionados."
          emptyIcon={<DollarSign className="h-10 w-10 text-muted-foreground" />}
        />
      </div>
    </div>
  );
}
