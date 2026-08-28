"use client";

import { Activity, Filter, IdCard, MapPin } from "lucide-react";
/**
 * DelegadosFiltroModal — Modal de filtros para la lista de delegados.
 * Usa AppFormModal como shell.
 *
 * Filtros: cip, municipalidad_id, estado
 * Al aplicar: onApply(filtros) → la vista muestra los filtros activos arriba.
 */
import { useCallback } from "react";
import { z } from "zod";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { useMunicipalidades } from "@/features/liquidaciones/hooks/useMunicipalidades";
import type { DelegadoEstado, DelegadoFiltros } from "../types/delegados.types";

const filtroSchema = z.object({
  cip: z.string().optional(),
  municipalidad_id: z.string().optional(),
  estado: z.string().optional(),
});

type FiltroFormData = z.infer<typeof filtroSchema>;

interface DelegadosFiltroModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialFiltros?: DelegadoFiltros;
  onApply: (filtros: DelegadoFiltros) => void;
}

const ESTADO_OPTIONS: { value: DelegadoEstado; label: string }[] = [
  { value: "vigente", label: "Vigente" },
  { value: "sin_vigencia", label: "Sin Vigencia" },
  { value: "sin_asignaciones", label: "Sin Asignaciones" },
];

export function DelegadosFiltroModal({
  open,
  onOpenChange,
  initialFiltros,
  onApply,
}: DelegadosFiltroModalProps) {
  const { data: municipalidades, isLoading: isLoadingMunicipalidades } =
    useMunicipalidades();

  const initialData: FiltroFormData = {
    cip: initialFiltros?.cip ?? "",
    municipalidad_id: initialFiltros?.municipalidad_id ?? "",
    estado: initialFiltros?.estado ?? "",
  };

  const handleSubmit = useCallback(
    async (data: FiltroFormData) => {
      const filtros: DelegadoFiltros = {};
      if (data.cip) filtros.cip = data.cip;
      if (data.municipalidad_id)
        filtros.municipalidad_id = data.municipalidad_id;
      if (data.estado) filtros.estado = data.estado as DelegadoEstado;
      onApply(filtros);
    },
    [onApply],
  );

  return (
    <AppFormModal<FiltroFormData>
      open={open}
      onOpenChange={onOpenChange}
      title="Filtrar Delegados"
      description="Filtra la lista por CIP, municipalidad o estado"
      eyebrow="Delegados"
      icon={<Filter className="h-5 w-5 text-primary" />}
      primaryLabel="Aplicar Filtros"
      primaryLoadingLabel="Aplicando..."
      primaryLoading={false}
      primaryDisabled={false}
      onPrimary={() => undefined}
      schema={filtroSchema}
      initialData={initialData}
      onSubmit={handleSubmit}
      size="md"
    >
      {({ methods }) => (
        <div className="space-y-4">
          {/* CIP */}
          <div className="space-y-2">
            <Label htmlFor="filtro-cip">CIP</Label>
            <div className="relative">
              <IdCard className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                id="filtro-cip"
                placeholder="Ej. 006502"
                className="pl-10 w-full"
                {...methods.register("cip")}
              />
            </div>
          </div>

          {/* Municipalidad */}
          <div className="space-y-2">
            <Label htmlFor="filtro-municipalidad">Municipalidad</Label>
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground z-10" />
              <Select
                value={methods.watch("municipalidad_id") || ""}
                onValueChange={(v) => methods.setValue("municipalidad_id", v)}
              >
                <SelectTrigger
                  id="filtro-municipalidad"
                  className="pl-10 h-10 w-full"
                >
                  <SelectValue
                    placeholder={
                      isLoadingMunicipalidades
                        ? "Cargando..."
                        : "Seleccionar municipalidad"
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  {(municipalidades || []).map((m) => (
                    <SelectItem key={m.id} value={m.id}>
                      {m.codigo ? `${m.codigo} - ` : ""}
                      {m.nombre}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Estado */}
          <div className="space-y-2">
            <Label htmlFor="filtro-estado">Estado</Label>
            <div className="relative">
              <Activity className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground z-10" />
              <Select
                value={methods.watch("estado") || ""}
                onValueChange={(v) => methods.setValue("estado", v)}
              >
                <SelectTrigger id="filtro-estado" className="pl-10 h-10 w-full">
                  <SelectValue placeholder="Seleccionar estado" />
                </SelectTrigger>
                <SelectContent>
                  {ESTADO_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
      )}
    </AppFormModal>
  );
}
