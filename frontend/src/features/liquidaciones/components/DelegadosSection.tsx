"use client";

import { format } from "date-fns";
import { es } from "date-fns/locale";
import {
  Calendar as CalendarIcon,
  ChevronDown,
  ChevronUp,
  Loader2,
  Users,
} from "lucide-react";
import { useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import type { Asignacion } from "../schemas/asignacion-delegado.schema";
import type { DelegadoVigente } from "../schemas/delegado-vigente.schema";

export type { Asignacion };

// ── Types ────────────────────────────────────────────────────────────────────

export const dictamenOptions = [
  { value: "CONFORME", label: "Conforme" },
  { value: "NO_CONFORME", label: "No conforme" },
  { value: "PENDIENTE", label: "Pendiente" },
  { value: "AP_OB", label: "AP.OB." },
] as const;

interface DelegadosSectionProps {
  /** List of available delegates for the selected municipalidad */
  delegados: DelegadoVigente[];
  /** Currently selected delegate IDs */
  selectedIds: string[];
  /** Whether delegates are being loaded */
  isLoading?: boolean;
  /** Whether a municipalidad has been selected */
  hasMunicipalidad: boolean;
  /** Callback when user toggles a delegate */
  onToggleDelegado: (id: string) => void;
  /** Optional: asignaciones with metadata for selected delegates */
  asignaciones?: Asignacion[];
  /** Optional: callback when metadata field is updated */
  onUpdateAsignacion?: (
    delegadoId: string,
    field: keyof Omit<Asignacion, "delegado_id">,
    value: string | null,
  ) => void;
}

// ── Section header ────────────────────────────────────────────────────────────

function SectionHeader({ count }: { count?: number }) {
  return (
    <div className="flex items-center gap-2 border-b border-border/40 pb-3">
      <Users className="h-4 w-4 text-primary shrink-0" />
      <h3 className="text-sm font-semibold uppercase tracking-wide text-foreground">
        Delegados
      </h3>
      {typeof count === "number" && (
        <span className="ml-auto text-xs text-muted-foreground">
          ({count} seleccionado{count !== 1 ? "s" : ""})
        </span>
      )}
    </div>
  );
}

// ── DatePicker sub-component ─────────────────────────────────────────────────

interface DatePickerFieldProps {
  label: string;
  value: string | null | undefined;
  onChange: (value: string | null) => void;
}

function DatePickerField({ label, value, onChange }: DatePickerFieldProps) {
  const id = useId();
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-xs font-medium text-muted-foreground">
        {label}
      </label>
      <Popover>
        <PopoverTrigger asChild>
          <Button
            id={id}
            variant="outline"
            className={cn(
              "w-full h-9 justify-start text-left text-xs pl-8 font-normal rounded-lg",
              !value && "text-muted-foreground",
            )}
          >
            <CalendarIcon className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            {value
              ? format(new Date(value), "PPP", { locale: es })
              : "Seleccionar..."}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="single"
            selected={value ? new Date(value) : undefined}
            onSelect={(date) =>
              onChange(date ? format(date, "yyyy-MM-dd") : null)
            }
            locale={es}
            initialFocus
          />
        </PopoverContent>
      </Popover>
    </div>
  );
}

// ── Metadata Editor sub-component ────────────────────────────────────────────

interface DelegadoMetadataEditorProps {
  delegado: DelegadoVigente;
  metadata: Asignacion;
  onUpdate: (
    field: keyof Omit<Asignacion, "delegado_id">,
    value: string | null,
  ) => void;
}

function DelegadoMetadataEditor({
  delegado,
  metadata,
  onUpdate,
}: DelegadoMetadataEditorProps) {
  const [open, setOpen] = useState(false);
  const hasMetadata =
    metadata.periodo ||
    metadata.dictamen_revision ||
    metadata.fecha_presentacion ||
    metadata.fecha_revision;

  return (
    <div className="rounded-xl border border-border/50 bg-card p-4 space-y-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center justify-between w-full text-left border-b border-border/40 pb-2"
      >
        <span className="text-xs font-semibold text-primary truncate">
          {delegado.nombre_completo} — Detalles
        </span>
        {open ? (
          <ChevronUp className="h-3.5 w-3.5 text-primary/70 shrink-0 ml-2" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5 text-primary/70 shrink-0 ml-2" />
        )}
      </button>

      {open && (
        <div className="grid grid-cols-2 gap-2 pt-1">
          {/* Periodo */}
          <div className="space-y-1.5">
            <label
              htmlFor={`periodo-${delegado.id}`}
              className="text-xs font-medium text-muted-foreground"
            >
              Período
            </label>
            <input
              id={`periodo-${delegado.id}`}
              type="text"
              value={metadata.periodo ?? ""}
              onChange={(e) => onUpdate("periodo", e.target.value || null)}
              placeholder="Ej: 2024-I"
              className="h-9 w-full rounded-lg border border-input bg-transparent px-3 text-xs shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/50"
            />
          </div>

          {/* Dictamen */}
          <div className="space-y-1.5">
            <span className="text-xs font-medium text-muted-foreground">
              Dictamen
            </span>
            <Select
              aria-label="Dictamen"
              value={metadata.dictamen_revision ?? ""}
              onValueChange={(v) => onUpdate("dictamen_revision", v || null)}
            >
              <SelectTrigger className="h-9 rounded-lg text-xs">
                <SelectValue placeholder="Seleccionar..." />
              </SelectTrigger>
              <SelectContent>
                {dictamenOptions.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Fecha presentación */}
          <DatePickerField
            label="Fecha presentación"
            value={metadata.fecha_presentacion}
            onChange={(v) => onUpdate("fecha_presentacion", v)}
          />

          {/* Fecha revisión */}
          <DatePickerField
            label="Fecha revisión"
            value={metadata.fecha_revision}
            onChange={(v) => onUpdate("fecha_revision", v)}
          />
        </div>
      )}

      {!open && hasMetadata && (
        <p className="text-[10px] text-muted-foreground italic truncate">
          Período: {metadata.periodo ?? "—"} • Dictamen:{" "}
          {dictamenOptions.find((o) => o.value === metadata.dictamen_revision)
            ?.label ?? "—"}
        </p>
      )}
    </div>
  );
}

/**
 * Delegados section for liquidacion form.
 * Shows available delegates for the selected municipalidad and allows multi-select.
 * Delegates are grouped by specialty (especialidad.nombre).
 */
export function DelegadosSection({
  delegados,
  selectedIds,
  isLoading = false,
  hasMunicipalidad,
  onToggleDelegado,
  asignaciones = [],
  onUpdateAsignacion,
}: DelegadosSectionProps) {
  // No municipalidad selected yet
  if (!hasMunicipalidad) {
    return (
      <div className="space-y-4">
        <SectionHeader />
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted/40 mb-3">
            <Users className="h-5 w-5 text-muted-foreground/70" />
          </div>
          <p className="text-sm text-muted-foreground">
            Seleccione una municipalidad para ver los delegados disponibles
          </p>
        </div>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-4">
        <SectionHeader />
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted/40 mb-3">
            <Loader2 className="h-5 w-5 text-muted-foreground animate-spin" />
          </div>
          <p className="text-sm text-muted-foreground">Cargando delegados...</p>
        </div>
      </div>
    );
  }

  // No delegates available
  if (delegados.length === 0) {
    return (
      <div className="space-y-4">
        <SectionHeader />
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted/40 mb-3">
            <Users className="h-5 w-5 text-muted-foreground/70" />
          </div>
          <p className="text-sm text-muted-foreground">
            No hay delegados vigentes para esta municipalidad
          </p>
        </div>
      </div>
    );
  }

  // Group delegates by specialty
  const groupedByEspecialidad = delegados.reduce<
    Record<string, DelegadoVigente[]>
  >((acc, delegado) => {
    const specialtyName = delegado.especialidad.nombre;
    if (!acc[specialtyName]) {
      acc[specialtyName] = [];
    }
    acc[specialtyName].push(delegado);
    return acc;
  }, {});

  // Sort specialties alphabetically
  const sortedSpecialties = Object.keys(groupedByEspecialidad).sort((a, b) =>
    a.localeCompare(b, undefined, { sensitivity: "base" }),
  );

  return (
    <div className="space-y-4">
      {/* Header */}
      <SectionHeader count={selectedIds.length} />

      {/* Grouped Delegates */}
      <div className="space-y-6">
        {sortedSpecialties.map((specialtyName) => {
          const specialtyDelegados = groupedByEspecialidad[specialtyName];
          return (
            <div key={specialtyName} className="space-y-3">
              {/* Specialty Group Header */}
              <div className="flex items-center gap-2">
                <div className="h-px flex-1 bg-border/60" />
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground shrink-0">
                  {specialtyName}
                </span>
                <div className="h-px flex-1 bg-border/60" />
              </div>

              {/* Delegates in this specialty */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 w-full">
                {specialtyDelegados.map((delegado) => {
                  const isSelected = selectedIds.includes(delegado.id);
                  return (
                    <button
                      key={delegado.id}
                      type="button"
                      onClick={() => onToggleDelegado(delegado.id)}
                      className={cn(
                        "w-full flex items-center justify-between gap-3 p-3 rounded-xl border bg-card transition-all text-left",
                        isSelected
                          ? "border-primary ring-1 ring-primary/30 bg-primary/5"
                          : "border-border hover:border-primary/40",
                      )}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        {/* Avatar */}
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 border border-primary/20">
                          <Users className="h-4 w-4 text-primary" />
                        </div>
                        <div className="flex flex-col min-w-0">
                          {/* Name */}
                          <span className="text-sm font-semibold truncate">
                            {delegado.nombre_completo}
                          </span>
                          {/* Metadata - subtle with badges, responsive wrapping */}
                          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 mt-1">
                            <span className="inline-flex items-center rounded-full bg-primary/10 border border-primary/20 px-2 py-0.5 text-[10px] font-bold text-primary whitespace-nowrap">
                              CIP {delegado.cip}
                            </span>
                            <span className="inline-flex items-center rounded-full bg-primary/10 border border-primary/20 px-2 py-0.5 text-[10px] font-bold text-primary capitalize whitespace-nowrap">
                              {delegado.tipo}
                            </span>
                          </div>
                        </div>
                      </div>
                      {/* Radio dot indicator */}
                      <span
                        className={cn(
                          "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border transition-all",
                          isSelected ? "border-primary" : "border-border",
                        )}
                      >
                        {isSelected && (
                          <span className="h-2 w-2 rounded-full bg-primary" />
                        )}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected delegates metadata editor */}
      {onUpdateAsignacion && selectedIds.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-border/60">
          <div className="flex items-center gap-2">
            <div className="h-px flex-1 bg-border/60" />
            <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground shrink-0">
              Detalles de delegados seleccionados
            </span>
            <div className="h-px flex-1 bg-border/60" />
          </div>
          <div className="space-y-2">
            {delegados
              .filter((d) => selectedIds.includes(d.id))
              .map((delegado) => {
                const metadata =
                  asignaciones.find((a) => a.delegado_id === delegado.id) ??
                  ({
                    delegado_id: delegado.id,
                    periodo: null,
                    dictamen_revision: null,
                    fecha_presentacion: null,
                    fecha_revision: null,
                  } satisfies Asignacion);
                return (
                  <DelegadoMetadataEditor
                    key={delegado.id}
                    delegado={delegado}
                    metadata={metadata}
                    onUpdate={(field, value) =>
                      onUpdateAsignacion(delegado.id, field, value)
                    }
                  />
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
}
