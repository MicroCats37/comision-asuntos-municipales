"use client";

import { Check, CheckCircle2, Layers, Pencil, Percent } from "lucide-react";
import { useEffect, useState } from "react";
import type { UseFormReturn } from "react-hook-form";
import { useWatch } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useTarifasVigentesPorcentaje } from "../../hooks/useTarifasVigentes";
import type { TipoTramiteEdificaciones } from "../../schemas/tramite.schema";

const TIPO_GRUPO_A: TipoTramiteEdificaciones[] = [
  "OBRA_NUEVA",
  "DEMOLICION",
  "REINTEGRO",
  "AMPLIACION",
  "REMODELACION",
  "PROYECTO_CON_PLANTAS_TIPICAS",
];

const TIPO_GRUPO_B: TipoTramiteEdificaciones[] = [
  "MODIFICACION_LICENCIA",
  "VARIACION_PROYECTO_APROBADO",
];

export type TarifasSmartFieldMode =
  | "create"
  | "edit"
  | "nueva-revision"
  | "relacionada";

interface TarifasYEspecialidadesSmartFieldProps {
  // biome-ignore lint/suspicious/noExplicitAny: UseFormReturn pattern matches existing smart fields
  methods: UseFormReturn<any>;
  /** Slug del tipo para el endpoint de tarifas vigentes ("edificaciones" por defecto) */
  tipo?: string;
  /** Modo del form. Default "create". */
  mode?: TarifasSmartFieldMode;
  /** Fecha de registro — solo aplica en mode="edit" (para tarifas históricas) */
  fecha?: string;
  /**
   * "auto" (default create): bloque compacto + auto-select all para Group A / sin tipo_tramite.
   * "manual": siempre expandido, sin auto-select. Usar en edit, nueva-revision, relacionada.
   * Si Group B en modo create, se fuerza expandido independientemente del variant.
   */
  variant?: "auto" | "manual";
}

const formatPercent = (value: number): string => `${(value * 100).toFixed(4)}%`;

function isGroupA(tipo: TipoTramiteEdificaciones | undefined): boolean {
  return tipo === undefined || (TIPO_GRUPO_A as string[]).includes(tipo);
}

function isGroupB(tipo: TipoTramiteEdificaciones | undefined): boolean {
  return tipo !== undefined && (TIPO_GRUPO_B as string[]).includes(tipo);
}

/**
 * TarifasYEspecialidadesSmartField — Collapsible unified smart field merging
 * PrimeraRevisionTarifasSmartField + EspecialidadesPorTipoTramiteSmartField.
 *
 * Compact view (variant="auto" + Group A / sin tipo_tramite): reactive summary chips
 * + tariff badge + "Editar selección" button to expand.
 *
 * Expanded view (variant="manual", edit/nueva-revision/relacionada, o Group B en create):
 * checkbox layer sin botón toggle — el usuario interactúa directamente.
 *
 * Mensajes informativos (cuando el smart field no puede reaccionar):
 *   - hasTipoTramite + tipo_tramite=null + create  → "Selecciona un tipo de trámite"
 *   - requiresValorDeclarado + valor_declarado<=0 → "Ingresa un valor declarado mayor a 0"
 */
export function TarifasYEspecialidadesSmartField({
  methods,
  tipo = "edificaciones",
  mode = "create",
  fecha,
  variant = "auto",
}: TarifasYEspecialidadesSmartFieldProps) {
  const hookProps = mode === "edit" && fecha ? { fecha } : {};
  const { data, isLoading } = useTarifasVigentesPorcentaje(tipo, hookProps);

  const tipoTramite = useWatch({
    control: methods.control,
    name: "tipo_tramite",
  }) as TipoTramiteEdificaciones | undefined;

  const tarifas = data?.tarifas ?? [];
  const especialidades = data?.especialidades_disponibles ?? [];
  const tarifaUnica = tarifas[0];
  const grupoA = isGroupA(tipoTramite);
  const grupoB = isGroupB(tipoTramite);

  const isRevisionLike = mode === "nueva-revision" || mode === "relacionada";

  const startExpanded =
    variant === "manual" ||
    mode === "edit" ||
    isRevisionLike ||
    (mode === "create" && grupoB);

  const [expanded, setExpanded] = useState(startExpanded);
  useEffect(() => {
    setExpanded(startExpanded);
  }, [startExpanded]);

  const selectedIds = useWatch({
    control: methods.control,
    name: "especialidades_seleccionadas",
  }) as (string | number)[] | undefined;
  const selectedSet = new Set(selectedIds ?? []);
  const especialidadesAplicadas = especialidades.filter((e) =>
    selectedSet.has(e.id),
  );

  const totalAplicado =
    especialidadesAplicadas.length > 0
      ? (tarifaUnica?.porcentaje_liquidacion ?? 0) *
        especialidadesAplicadas.length
      : 0;

  // Effect 1: set tarifa_unica_id whenever tariff changes
  useEffect(() => {
    if (!tarifaUnica) return;
    methods.setValue("tarifa_unica_id", tarifaUnica.id, {
      shouldValidate: false,
    });
  }, [tarifaUnica, methods]);

  // Effect 2: auto-select solo en modo compacto (variant="auto" + Group A / sin tipo_tramite),
  // en mode="create", y solo cuando NO hay selección previa (respeta la elección del usuario).
  // En nueva-revision / relacionada / edit: NUNCA auto-select (el usuario debe elegir).
  useEffect(() => {
    const hasSelection = selectedIds && selectedIds.length > 0;
    if (!tarifaUnica || especialidades.length === 0) return;
    if (startExpanded) return;
    if (hasSelection) return;
    if (mode !== "create") return;

    if (grupoA) {
      methods.setValue(
        "especialidades_seleccionadas",
        especialidades.map((e) => e.id),
        { shouldValidate: false },
      );
    }
  }, [
    tarifaUnica,
    especialidades,
    selectedIds,
    grupoA,
    startExpanded,
    mode,
    methods,
  ]);

  // ── Estados informativos: ahora viven en CotizacionPorcentajeSmartField ─
  // Este smart field solo se ocupa de mostrar/seleccionar tarifas y especialidades.
  // La cotización muestra los mensajes de "qué falta" (tipo_tramite, valor_declarado, especialidades).

  if (isLoading) {
    return (
      <div className="space-y-3 rounded-xl border border-border/50 bg-card p-4 animate-pulse">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-primary" />
          <div className="h-4 w-32 bg-muted rounded" />
        </div>
        <div className="h-4 w-48 bg-muted rounded" />
        <div className="h-4 w-40 bg-muted rounded" />
      </div>
    );
  }

  if (!tarifaUnica) {
    return (
      <div className="space-y-2 rounded-xl border border-border/50 bg-card p-4">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold uppercase tracking-wide">
            Tarifas Vigentes
          </h3>
        </div>
        <p className="text-sm text-muted-foreground text-center py-3">
          No hay tarifas vigentes disponibles
        </p>
      </div>
    );
  }

  const labelText = isRevisionLike
    ? "Selecciona las especialidades a aplicar"
    : selectedIds?.length === especialidades.length
      ? "Todas las Especialidades"
      : selectedIds?.length === 0
        ? "Especialidades a aplicar"
        : `Especialidades a aplicar · ${selectedIds?.length ?? 0} de ${especialidades.length}`;

  return (
    <div className="space-y-3 rounded-xl border border-primary/20 bg-primary/[0.03] p-4 shadow-sm">
      <div className="flex items-center justify-between gap-2 border-b border-border/40 pb-2">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold uppercase tracking-wide">
            {labelText}
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-0.5 text-xs font-bold text-primary">
            <Percent className="h-3 w-3" />
            {formatPercent(totalAplicado)}
            <span className="font-normal text-primary/70">
              × {especialidadesAplicadas.length} esp.
            </span>
          </span>
          {!startExpanded &&
            (expanded ? (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-7 gap-1 text-xs"
                onClick={() => setExpanded(false)}
              >
                <Check className="h-3 w-3" />
                Listo
              </Button>
            ) : (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-7 gap-1 text-xs"
                onClick={() => setExpanded(true)}
              >
                <Pencil className="h-3 w-3" />
                Editar selección
              </Button>
            ))}
        </div>
      </div>

      {startExpanded || expanded ? (
        <fieldset className="space-y-2">
          <div className="flex flex-row flex-wrap gap-2">
            {especialidades.map((esp) => {
              const isSelected = selectedSet.has(esp.id);
              return (
                <label
                  key={esp.id}
                  className={cn(
                    "rounded-lg border bg-background px-3 py-2.5 transition-all duration-200 text-left flex-1 min-w-[160px] flex items-center gap-2 cursor-pointer",
                    isSelected
                      ? "border-primary ring-1 ring-primary/30 bg-primary/5"
                      : "border-border hover:border-primary/40",
                  )}
                >
                  <span
                    className={cn(
                      "flex h-4 w-4 shrink-0 items-center justify-center rounded border",
                      isSelected ? "border-primary" : "border-border",
                    )}
                  >
                    {isSelected && (
                      <span className="h-2 w-2 rounded-sm bg-primary" />
                    )}
                  </span>
                  <span className="text-sm font-medium truncate">
                    {esp.nombre}
                  </span>
                  <span className="text-xs text-muted-foreground shrink-0">
                    ({esp.codigo})
                  </span>
                  <input
                    type="checkbox"
                    className="sr-only"
                    checked={isSelected}
                    onChange={() => {
                      const current = selectedIds ?? [];
                      const next = isSelected
                        ? current.filter((id) => id !== esp.id)
                        : [...current, esp.id];
                      methods.setValue("especialidades_seleccionadas", next, {
                        shouldValidate: true,
                      });
                    }}
                  />
                </label>
              );
            })}
          </div>
        </fieldset>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {especialidadesAplicadas.map((esp) => (
            <span
              key={esp.id}
              className="inline-flex items-center gap-1 rounded-md border border-primary/20 bg-background px-2 py-1 text-xs font-medium"
            >
              <Layers className="h-3 w-3 text-primary/60" />
              {esp.nombre}
              <span className="text-muted-foreground">·</span>
              <span className="font-bold text-primary">{esp.codigo}</span>
            </span>
          ))}
          {especialidadesAplicadas.length === 0 && (
            <p className="text-xs text-muted-foreground italic py-1">
              Ninguna especialidad seleccionada
            </p>
          )}
        </div>
      )}
    </div>
  );
}
