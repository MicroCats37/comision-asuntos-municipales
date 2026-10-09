"use client";

import { HardHat, Layers, UserCheck } from "lucide-react";
/**
 * SeleccionarInspectorModal — Modal para elegir UN inspector en el form de
 * creación de Inspección de Obra.
 *
 * - Selector de Tipo de Liquidación DENTRO del modal (chips seleccionables).
 * - Consulta GET /liquidaciones/inspectores/seleccionables?tipo_liquidacion=
 *   (carga solo después de que el usuario selecciona un tipo)
 * - Filtros SEPARADOS en el frontend: por especialidad y por categoría
 * - Lista agrupada por especialidad, single-select
 * - Adjunta inspector_id al form (react-hook-form) al confirmar
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { InspectorVigente } from "@/features/inspectores/types/inspectores.types";
import { useInspectoresVigentes } from "../../hooks/useInspectoresVigentes";
import type { TipoLiquidacionMinimalSchema } from "../../schemas/liquidacion-base.schema";

type TipoLiquidacionMinimal = {
  id: string;
  codigo: string;
  nombre: string;
};

interface SeleccionarInspectorModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Tipos de liquidación disponibles (de `useTiposLiquidacion`). Si está vacío, no se muestra selector. */
  tiposLiquidacion?: TipoLiquidacionMinimal[];
  /** ID del tipo actualmente seleccionado */
  tipoLiquidacionId?: string | null;
  /** Callback al cambiar el tipo — actualiza el form del padre */
  onTipoLiquidacionChange?: (id: string) => void;
  /** Fallback: codigo del tipo cuando no hay selector visible (ej. edit form con tipo fijo) */
  fallbackTipoLiquidacionCodigo?: string | null;
  /** Categoría seleccionada en el form (dinámica via watch) — precarga el filtro */
  categoriaForm?: string | null;
  /** Inspector ya seleccionado (para resaltarlo) */
  selectedId?: string;
  onSelect: (inspectorId: string, nombreCompleto: string, inspectorOperacionId: string) => void;
}

export function SeleccionarInspectorModal({
  open,
  onOpenChange,
  tiposLiquidacion = [],
  tipoLiquidacionId,
  onTipoLiquidacionChange,
  fallbackTipoLiquidacionCodigo,
  categoriaForm,
  selectedId,
  onSelect,
}: SeleccionarInspectorModalProps) {
  const [especialidad, setEspecialidad] = useState("all");
  const [q, setQ] = useState("");
  const [pickedId, setPickedId] = useState<string>(selectedId ?? "");

  // La categoría es FIJA: viene de la selección del form (no editable en el modal)
  const categoria = categoriaForm ?? "all";

  // Resolver el codigo del tipo seleccionado.
  // Prioridad: lookup por id en tipos → fallback directo.
  const tipoSeleccionado = tiposLiquidacion.find(
    (t) => t.id === tipoLiquidacionId,
  );
  const tipoLiquidacionCodigo =
    tipoSeleccionado?.codigo ?? fallbackTipoLiquidacionCodigo ?? null;

  // Carga todos los vigentes del tipo (sin filtro de categoría en backend)
  const { data: inspectores = [], isLoading } = useInspectoresVigentes(
    tipoLiquidacionCodigo,
    null,
    undefined,
    open && !!tipoLiquidacionCodigo,
  );

  // Reset al abrir — mantiene la categoría del form (fija)
  const prevOpen = usePrevious(open);
  useEffect(() => {
    if (open && !prevOpen) {
      setEspecialidad("all");
      setQ("");
      setPickedId(selectedId ?? "");
    }
  }, [open, prevOpen, selectedId]);

  // Especialidades únicas para el filtro
  const especialidades = useMemo(
    () =>
      [
        ...new Set(
          inspectores.map((i) => i.especialidad?.nombre).filter(Boolean),
        ),
      ].sort(),
    [inspectores],
  );

  // Normaliza la categoría del inspector para que haga match con el filtro (que viene en formato "C1", "C2"…)
  const normalizeCategoria = (cat: string | null): string => {
    if (!cat) return "";
    if (["1", "2", "3", "4"].includes(cat)) return `C${cat}`;
    return cat;
  };

  // Filtrado en el FRONTEND: por categoría FIJA + especialidad + búsqueda CIP/nombre
  const filtrados = useMemo(() => {
    const query = q.trim().toLowerCase();
    return inspectores.filter((i) => {
      if (categoria !== "all" && normalizeCategoria(i.categoria) !== categoria)
        return false;
      if (especialidad !== "all" && i.especialidad?.nombre !== especialidad)
        return false;
      if (query) {
        const hayMatch =
          (i.cip ?? "").toLowerCase().includes(query) ||
          i.nombre_completo.toLowerCase().includes(query);
        if (!hayMatch) return false;
      }
      return true;
    });
  }, [inspectores, especialidad, categoria, q]);

  // Agrupación por especialidad
  const grouped = useMemo(() => {
    const map: Record<string, InspectorVigente[]> = {};
    for (const insp of filtrados) {
      const key = insp.especialidad?.nombre ?? "Sin especialidad";
      if (!map[key]) map[key] = [];
      map[key].push(insp);
    }
    return map;
  }, [filtrados]);

  const handleConfirm = useCallback(() => {
    if (!pickedId) return;
    const picked = inspectores.find((i) => i.id === pickedId);
    onSelect(pickedId, picked?.nombre_completo ?? "", picked?.inspector_operacion_id ?? "");
    onOpenChange(false);
  }, [pickedId, inspectores, onSelect, onOpenChange]);

  return (
    <div
      className={[
        "fixed inset-0 z-50 flex items-center justify-center p-4",
        open ? "pointer-events-auto" : "pointer-events-none",
      ].join(" ")}
    >
      <button
        type="button"
        aria-label="Cerrar"
        className={[
          "absolute inset-0 bg-black/40 transition-opacity cursor-default",
          open ? "opacity-100" : "opacity-0",
        ].join(" ")}
        onClick={() => onOpenChange(false)}
      />

      <div
        className={[
          "relative w-full max-w-2xl rounded-2xl border border-border bg-card shadow-xl transition-all",
          open ? "scale-100 opacity-100" : "scale-95 opacity-0",
        ].join(" ")}
      >
        {/* Header */}
        <div className="flex items-center gap-2 border-b border-border/60 px-5 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 border border-primary/20 text-primary">
            <UserCheck className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-base font-bold text-foreground">
              Seleccionar Inspector
            </h2>
            <p className="text-xs text-muted-foreground">
              Elige el inspector que revisará la inspección de obra.
            </p>
          </div>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4 max-h-[60vh] overflow-y-auto">
          {/* Selector de Tipo de Liquidación (solo si hay tipos disponibles + callback) */}
          {tiposLiquidacion.length > 0 && onTipoLiquidacionChange && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Layers className="h-3.5 w-3.5 text-primary/70" />
                <span className="text-xs font-semibold text-muted-foreground">
                  Tipo de Liquidación:
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {tiposLiquidacion.map((t) => {
                  const isSelected = tipoLiquidacionId === t.id;
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => onTipoLiquidacionChange(t.id)}
                      className={cn(
                        "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                        isSelected
                          ? "border-primary bg-primary/10 text-primary"
                          : "border-border text-muted-foreground hover:border-primary/40",
                      )}
                    >
                      {t.codigo} · {t.nombre}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Filtros */}
          <div className="space-y-3">
            {/* Buscador por CIP / nombre */}
            <div className="flex gap-2">
              <input
                type="text"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Buscar por CIP o nombre..."
                className="min-w-0 flex-1 h-10 rounded-xl border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              />
            </div>

            {/* Categoría FIJA (de la selección del form) + filtro por especialidad */}
            <div className="flex flex-wrap items-center gap-2">
              {categoria !== "all" && (
                <span className="inline-flex items-center rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
                  Categoría {categoria} (seleccionada)
                </span>
              )}

              {especialidades.length > 1 && (
                <>
                  <span className="text-xs font-semibold text-muted-foreground">
                    Especialidad:
                  </span>
                  <button
                    type="button"
                    onClick={() => setEspecialidad("all")}
                    className={[
                      "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                      especialidad === "all"
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border text-muted-foreground hover:border-primary/40",
                    ].join(" ")}
                  >
                    Todas
                  </button>
                  {especialidades.map((esp) => (
                    <button
                      key={esp}
                      type="button"
                      onClick={() => setEspecialidad(esp)}
                      className={[
                        "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                        especialidad === esp
                          ? "border-primary bg-primary/10 text-primary"
                          : "border-border text-muted-foreground hover:border-primary/40",
                      ].join(" ")}
                    >
                      {esp}
                    </button>
                  ))}
                </>
              )}
            </div>
          </div>

          {/* Estados */}
          {!tipoLiquidacionCodigo && (
            <div className="rounded-lg border border-primary/20 bg-primary/[0.03] p-4 text-center">
              <p className="text-sm text-muted-foreground">
                Selecciona un tipo de liquidación para cargar los inspectores.
              </p>
            </div>
          )}
          {tipoLiquidacionCodigo && isLoading && (
            <p className="text-sm text-muted-foreground animate-pulse">
              Cargando inspectores...
            </p>
          )}
          {tipoLiquidacionCodigo &&
            !isLoading &&
            inspectores.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No hay inspectores vigentes para este tipo de liquidación.
              </p>
            )}
          {!isLoading && inspectores.length > 0 && filtrados.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No hay inspectores con los filtros seleccionados.
            </p>
          )}

          {/* Lista agrupada por especialidad */}
          {!isLoading &&
            Object.entries(grouped).map(([esp, lista]) => (
              <div key={esp} className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className="h-px flex-1 bg-border/60" />
                  <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground shrink-0">
                    {esp}
                  </span>
                  <div className="h-px flex-1 bg-border/60" />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {lista.map((inspector) => {
                    const isSelected = pickedId === inspector.id;
                    return (
                      <button
                        key={inspector.id}
                        type="button"
                        onClick={() => setPickedId(inspector.id)}
                        className={[
                          "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl border transition-all text-left",
                          isSelected
                            ? "bg-primary/10 border-primary/60 ring-2 ring-primary/30"
                            : "bg-card border-border/70 hover:border-primary/40",
                        ].join(" ")}
                      >
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-muted/80 text-muted-foreground">
                          <HardHat className="h-4 w-4" />
                        </div>
                        <div className="flex flex-col min-w-0 flex-1">
                          <span className="text-sm font-bold text-foreground truncate">
                            {inspector.nombre_completo}
                          </span>
                          <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground mt-0.5">
                            <span>CIP {inspector.cip}</span>
                            <span>{inspector.numero_registro}</span>
                            {inspector.categoria && (
                              <span className="rounded bg-secondary/70 px-1.5 py-0.5">
                                Cat. {inspector.categoria}
                              </span>
                            )}
                          </div>
                        </div>
                        <span
                          className={[
                            "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border",
                            isSelected ? "border-primary" : "border-border",
                          ].join(" ")}
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
            ))}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-border/60 px-5 py-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Cancelar
          </Button>
          <Button type="button" onClick={handleConfirm} disabled={!pickedId}>
            Asignar Inspector
          </Button>
        </div>
      </div>
    </div>
  );
}

function usePrevious<T>(value: T): T | undefined {
  const ref = useRef<T | undefined>(undefined);
  const prev = ref.current;
  ref.current = value;
  return prev;
}
