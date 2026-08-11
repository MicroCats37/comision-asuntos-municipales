"use client";

import { useCallback, useMemo, useState } from "react";
import { UserCheck } from "lucide-react";
import { z } from "zod";
import type { UseFormReturn } from "react-hook-form";

import { AppFormModal } from "@/components-app/forms/AppFormModal";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";
import { handleApiError } from "@/errors";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { InspectorVigente } from "../types/liquidacion-general";
import { useInspectoresVigentes } from "../hooks/useInspectoresVigentes";

interface HasId {
  id: string;
}

const seleccionarInspectorSchema = z.object({
  inspector_id: z.string().nullable(),
});

interface InspectorSelectorModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** UUID of the liquidacion previa to derive tipo_liquidacion */
  liquidacionPreviaId: string;
  /** Currently pre-selected inspector ID (optional) */
  selectedInspectorId: string | null;
  /** Full inspector object for display (optional) */
  selectedInspector: InspectorVigente | null;
  onSelectInspector: (inspectorId: string | null, inspector: InspectorVigente | null) => void;
}

export function InspectorSelectorModal({
  open,
  onOpenChange,
  liquidacionPreviaId,
  selectedInspectorId,
  selectedInspector,
  onSelectInspector,
}: InspectorSelectorModalProps) {
  // ── Filter state ────────────────────────────────────────────────────────────
  const [filterCategoria, setFilterCategoria] = useState<string>("all");
  const [filterNombre, setFilterNombre] = useState("");
  const [filterCip, setFilterCip] = useState("");

  const {
    data: inspectoresVigentes = [],
    isLoading,
    error,
  } = useInspectoresVigentes(
    null, // liquidacionId - not for existing liquidacion
    undefined, // tipoLiquidacion - derived from liquidacion_previa_id
    liquidacionPreviaId || undefined, // liquidacionPreviaId - to derive tipo_liquidacion
  );

  // Unique categories derived from data
  const categoriasUnicas = useMemo(() => {
    const cats = new Set<string>();
    inspectoresVigentes.forEach((i) => {
      const name = i.especialidad?.nombre ?? "Sin especialidad";
      cats.add(name);
    });
    return Array.from(cats).sort((a, b) =>
      a === "Sin especialidad" ? 1 : b === "Sin especialidad" ? -1 : a.localeCompare(b),
    );
  }, [inspectoresVigentes]);

  // Filtered + re-grouped inspectors
  const filteredInspectores = useMemo(() => {
    return inspectoresVigentes.filter((inspector) => {
      const matchesCategoria =
        filterCategoria === "all" ||
        (inspector.especialidad?.nombre ?? "Sin especialidad") === filterCategoria;
      const matchesNombre =
        !filterNombre ||
        inspector.nombre_completo.toLowerCase().includes(filterNombre.toLowerCase());
      const matchesCip =
        !filterCip || inspector.cip.toLowerCase().includes(filterCip.toLowerCase());
      return matchesCategoria && matchesNombre && matchesCip;
    });
  }, [inspectoresVigentes, filterCategoria, filterNombre, filterCip]);

  const groupedByEspecialidad = useMemo(() => {
    const grouped = filteredInspectores.reduce<Record<string, InspectorVigente[]>>((acc, inspector) => {
      const specialtyName = inspector.especialidad?.nombre ?? "Sin especialidad";
      if (!acc[specialtyName]) acc[specialtyName] = [];
      acc[specialtyName].push(inspector);
      return acc;
    }, {});
    return Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b, undefined, { sensitivity: "base" }));
  }, [filteredInspectores]);

  const inspectoresById = useMemo(() => {
    return new Map(inspectoresVigentes.map((inspector) => [inspector.id, inspector]));
  }, [inspectoresVigentes]);

  const handleSubmit = useCallback(
    async (data: { inspector_id: string | null }) => {
      const inspectorId = data.inspector_id;
      const inspector = inspectorId ? (inspectoresById.get(inspectorId) ?? null) : null;
      onSelectInspector(inspectorId, inspector);
      onOpenChange(false);
    },
    [inspectoresById, onSelectInspector, onOpenChange],
  );

  const handleClear = useCallback(() => {
    onSelectInspector(null, null);
    onOpenChange(false);
  }, [onSelectInspector, onOpenChange]);

  const renderContent = useCallback(
    ({
      methods,
    }: {
      methods: UseFormReturn<{ inspector_id: string | null }>;
      isSubmitting: boolean;
      onSubmit: () => void;
      submissionMessage: { type: "success" | "error"; message: string } | null;
    }) => {
      const selectedId = methods.watch("inspector_id");

      const handleRadioChange = (value: string) => {
        methods.setValue("inspector_id", value, { shouldDirty: true });
      };

      if (isLoading) {
        return (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">Cargando inspectores...</span>
          </div>
        );
      }

      if (error) {
        return (
          <div className="py-8 text-center">
            <p className="text-sm text-destructive">Error al cargar inspectores</p>
            <p className="text-xs text-muted-foreground mt-1">{handleApiError(error).message}</p>
          </div>
        );
      }

      if (filteredInspectores.length === 0) {
        return (
          <div className="py-8 text-center">
            <p className="text-sm text-muted-foreground italic">
              {inspectoresVigentes.length === 0
                ? "No hay inspectores elegibles para esta liquidación previa"
                : "Ningún inspector coincide con los filtros aplicados"}
            </p>
          </div>
        );
      }

      return (
        <div className="space-y-4">
          {/* ── Filters ──────────────────────────────────────────────────── */}
          <div className="flex flex-wrap gap-3 rounded-xl border border-border/50 bg-muted/20 p-3">
            {/* Category filter */}
            <div className="flex flex-col gap-1 min-w-[160px]">
              <label className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                Categoría
              </label>
              <Select
                value={filterCategoria}
                onValueChange={setFilterCategoria}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="Todas" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas</SelectItem>
                  {categoriasUnicas.map((cat) => (
                    <SelectItem key={cat} value={cat}>
                      {cat}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Name search */}
            <div className="flex flex-col gap-1 min-w-[160px]">
              <label className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                Nombre
              </label>
              <Input
                type="text"
                placeholder="Buscar por nombre..."
                value={filterNombre}
                onChange={(e) => setFilterNombre(e.target.value)}
                className="h-8 text-xs"
              />
            </div>

            {/* CIP search */}
            <div className="flex flex-col gap-1 min-w-[120px]">
              <label className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                CIP
              </label>
              <Input
                type="text"
                placeholder="CIP..."
                value={filterCip}
                onChange={(e) => setFilterCip(e.target.value)}
                className="h-8 text-xs"
              />
            </div>

            {/* Results count */}
            <div className="flex items-end pb-1">
              <span className="text-[10px] text-muted-foreground whitespace-nowrap">
                {filteredInspectores.length} de {inspectoresVigentes.length}
              </span>
            </div>
          </div>
        <RadioGroup
          value={selectedId ?? ""}
          onValueChange={handleRadioChange}
          className="space-y-6"
        >
          {groupedByEspecialidad.map(([specialtyName, inspectors]) => (
            <div key={specialtyName} className="space-y-3">
              <div className="flex items-center gap-2">
                <div className="h-px flex-1 bg-border/60" />
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground shrink-0 px-2">
                  {specialtyName}
                </span>
                <div className="h-px flex-1 bg-border/60" />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 w-full">
                {inspectors.map((inspector) => {
                  const isSelected = selectedId === inspector.id;
                  return (
                    <div key={inspector.id} className="relative">
                      <RadioGroupItem
                        value={inspector.id}
                        id={inspector.id}
                        className="peer sr-only"
                      />
                      <Label
                        htmlFor={inspector.id}
                        className={[
                          "w-full flex items-center justify-between gap-3 px-3 py-2.5 rounded-xl border cursor-pointer transition-all text-left",
                          isSelected
                            ? "bg-primary/10 border-primary/60 ring-2 ring-primary/30"
                            : "bg-secondary/30 border-border/70 hover:bg-secondary/60 hover:border-primary/40",
                        ].join(" ")}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${isSelected ? "bg-primary text-primary-foreground" : "bg-muted/80 text-muted-foreground"}`}>
                            <UserCheck className="h-4 w-4" />
                          </div>
                          <div className="flex flex-col min-w-0">
                            <span className="text-sm font-bold text-foreground truncate">
                              {inspector.nombre_completo}
                            </span>
                            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground mt-1">
                              <span className="inline-flex items-center px-2 py-0.5 rounded bg-muted/70 text-foreground/80 font-medium whitespace-nowrap">
                                CIP {inspector.cip}
                              </span>
                              <span className="inline-flex items-center px-2 py-0.5 rounded bg-secondary/70 text-muted-foreground/80 whitespace-nowrap">
                                Reg. {inspector.numero_registro}
                              </span>
                            </div>
                          </div>
                        </div>
                        {isSelected && (
                          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-primary-foreground shrink-0">
                            <UserCheck className="h-3 w-3" />
                          </div>
                        )}
                      </Label>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </RadioGroup>
        </div>
      );
    },
    [filteredInspectores, inspectoresVigentes, categoriasUnicas, groupedByEspecialidad, error, isLoading, filterCategoria, filterNombre, filterCip, onSelectInspector],
  );

  return (
    <AppFormModal
      open={open}
      onOpenChange={onOpenChange}
      title="Seleccionar Inspector"
      description="Elige un inspector para esta inspección de obra."
      eyebrow="Inspección de Obra"
      icon={<UserCheck className="h-5 w-5 text-primary" />}
      primaryLabel="Confirmar"
      primaryLoadingLabel="Guardando..."
      primaryLoading={false}
      onPrimary={() => {}}
      schema={seleccionarInspectorSchema}
      initialData={{ inspector_id: selectedInspectorId }}
      onSubmit={handleSubmit}
      secondaryLabel={selectedInspectorId ? "Quitar inspector" : undefined}
      onSecondary={selectedInspectorId ? handleClear : undefined}
      size="xl"
    >
      {renderContent}
    </AppFormModal>
  );
}
