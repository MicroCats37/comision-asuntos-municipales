"use client";

import { format } from "date-fns";
import { es } from "date-fns/locale";
import { Calendar as CalendarIcon, Filter } from "lucide-react";
/**
 * TarifasFiltroModal — Modal de filtros para el Tarifario.
 * Usa AppFormModal como shell (mismo patrón que LiquidacionFiltroModal).
 *
 * Filtros:
 *   fechaDesde  → inicio del rango (opcional → histórico por rango)
 *   fechaHasta  → fin del rango (opcional)
 * Ya NO se filtra por tipo — la vista muestra TODAS las tarifas.
 */
import { useCallback, useRef } from "react";
import type { UseFormReturn } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Label } from "@/components/ui/label";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import type { TarifasFiltros } from "../types/finanzas.types";

const filtroSchema = z.object({
  fechaDesde: z.string().optional(),
  fechaHasta: z.string().optional(),
});

type FiltroFormData = z.infer<typeof filtroSchema>;

const DEFAULT_FILTROS: FiltroFormData = {
  fechaDesde: "",
  fechaHasta: "",
};

interface TarifasFiltroModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialFiltros?: TarifasFiltros;
  onApply: (filtros: TarifasFiltros) => void;
}

function CampoFecha({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <Popover>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            className="w-full h-10 justify-start text-left font-normal pl-9 relative"
          >
            <CalendarIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
            {value ? (
              format(new Date(value), "PPP", { locale: es })
            ) : (
              <span className="text-muted-foreground">Seleccionar...</span>
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="single"
            selected={value ? new Date(value) : undefined}
            onSelect={(date) =>
              onChange(date ? format(date, "yyyy-MM-dd") : "")
            }
            locale={es}
            initialFocus
          />
        </PopoverContent>
      </Popover>
    </div>
  );
}

export function TarifasFiltroModal({
  open,
  onOpenChange,
  initialFiltros,
  onApply,
}: TarifasFiltroModalProps) {
  const methodsRef = useRef<UseFormReturn<FiltroFormData> | null>(null);

  const initialData: FiltroFormData = {
    fechaDesde: initialFiltros?.fechaDesde ?? "",
    fechaHasta: initialFiltros?.fechaHasta ?? "",
  };

  const handleLimpiar = useCallback(() => {
    methodsRef.current?.reset(DEFAULT_FILTROS);
  }, []);

  const handleSubmit = useCallback(
    async (data: FiltroFormData) => {
      const filtros: TarifasFiltros = {
        fechaDesde: data.fechaDesde || undefined,
        fechaHasta: data.fechaHasta || undefined,
      };
      onApply(filtros);
    },
    [onApply],
  );

  return (
    <AppFormModal<FiltroFormData>
      open={open}
      onOpenChange={onOpenChange}
      title="Filtrar Tarifas"
      description="Filtra por rango de fechas. Sin fechas se muestran solo las tarifas vigentes; con fechas, el histórico por rango."
      eyebrow="Tarifario"
      icon={<Filter className="h-5 w-5 text-primary" />}
      primaryLabel="Aplicar"
      primaryLoadingLabel="Aplicando..."
      primaryLoading={false}
      primaryDisabled={false}
      onPrimary={() => undefined}
      secondaryLabel="Limpiar"
      onSecondary={handleLimpiar}
      schema={filtroSchema}
      initialData={initialData}
      onSubmit={handleSubmit}
      size="lg"
    >
      {({ methods }) => {
        methodsRef.current = methods;
        return (
          <div className="space-y-4">
            {/* Fechas */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <CampoFecha
                label="Fecha Desde"
                value={methods.watch("fechaDesde") || ""}
                onChange={(v) => methods.setValue("fechaDesde", v)}
              />
              <CampoFecha
                label="Fecha Hasta"
                value={methods.watch("fechaHasta") || ""}
                onChange={(v) => methods.setValue("fechaHasta", v)}
              />
            </div>
          </div>
        );
      }}
    </AppFormModal>
  );
}
