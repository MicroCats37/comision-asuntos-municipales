"use client";

import { CheckCircle2, Layers, Percent } from "lucide-react";
/**
 * EspecialidadesPorTipoTramiteSmartField — Smart Field de especialidades cuyo
 * comportamiento cambia según el `tipo_tramite` seleccionado.
 *
 * Sigue el patrón visual de PrimeraRevisionTarifasSmartField (rígido, chips
 * read-only), pero para el Grupo B cambia a radio (selección única).
 *
 * Group A (RIGID — todas las especialidades pre-seleccionadas, read-only):
 *   OBRA_NUEVA, DEMOLICION, REINTEGRO, AMPLIACION, REMODELACION,
 *   PROYECTO_CON_PLANTAS_TIPICAS
 *
 * Group B (RADIO — selección única):
 *   MODIFICACION_LICENCIA, VARIACION_PROYECTO_APROBADO
 *
 * Arquitectura:
 * - Recibe `methods: UseFormReturn<any>` desde el form.
 * - REACTIVO: hace `useWatch("tipo_tramite")` internamente — cambia de modo
 *   automáticamente cuando el usuario cambia el tipo de trámite.
 * - Sync al form via `methods.setValue` (tarifa_unica_id + especialidades_seleccionadas).
 * - Lee especialidades de `useTarifasVigentesPorcentaje("edificaciones")`.
 */
import { useEffect } from "react";
import { type UseFormReturn, useWatch } from "react-hook-form";
import { useTarifasVigentesPorcentaje } from "../../hooks/useTarifasVigentes";
import type { TipoTramiteEdificaciones } from "../../schemas/tramite.schema";

// ─── Group mapping — easy to adjust ───────────────────────────────────────────

/** Group A: rigid all-selected chips (read-only). */
const TIPO_GRUPO_A: TipoTramiteEdificaciones[] = [
  "OBRA_NUEVA",
  "DEMOLICION",
  "REINTEGRO",
  "AMPLIACION",
  "REMODELACION",
  "PROYECTO_CON_PLANTAS_TIPICAS",
];

/** Group B: radio single-selection. */
const TIPO_GRUPO_B: TipoTramiteEdificaciones[] = [
  "MODIFICACION_LICENCIA",
  "VARIACION_PROYECTO_APROBADO",
];

// ─── Props ─────────────────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface EspecialidadesPorTipoTramiteSmartFieldProps {
  methods: UseFormReturn<any>;
  /** Tipo de liquidación para el endpoint (default: edificaciones) */
  tipo?: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const formatPercent = (value: number): string => `${(value * 100).toFixed(4)}%`;

function isGroupA(tipo: TipoTramiteEdificaciones | undefined): boolean {
  return (TIPO_GRUPO_A as string[]).includes(tipo ?? "OBRA_NUEVA");
}

function isGroupB(tipo: TipoTramiteEdificaciones | undefined): boolean {
  return (TIPO_GRUPO_B as string[]).includes(tipo ?? "OBRA_NUEVA");
}

// ─── Component ────────────────────────────────────────────────────────────────

export function EspecialidadesPorTipoTramiteSmartField({
  methods,
  tipo = "edificaciones",
}: EspecialidadesPorTipoTramiteSmartFieldProps) {
  const { data, isLoading } = useTarifasVigentesPorcentaje(tipo);

  // Reactivo: cambia de modo al instante cuando cambia tipo_tramite
  const tipoTramite = useWatch({
    control: methods.control,
    name: "tipo_tramite",
  }) as TipoTramiteEdificaciones | undefined;

  const tarifas = data?.tarifas ?? [];
  const especialidades = data?.especialidades_disponibles ?? [];
  const tarifaUnica = tarifas[0];
  const grupoA = isGroupA(tipoTramite);
  const grupoB = isGroupB(tipoTramite);

  // Reactivo a la selección: la cotización refleja la especialidad elegida
  const especialidadesSeleccionadas = useWatch({
    control: methods.control,
    name: "especialidades_seleccionadas",
  }) as string[] | undefined;

  const idsSeleccionados = especialidadesSeleccionadas ?? [];
  // Group A: todas (rígido). Group B: las checkboxes marcadas; 0 → nada.
  const countAplicado = grupoA ? especialidades.length : idsSeleccionados.length;
  const totalAplicado =
    countAplicado > 0
      ? (tarifaUnica?.porcentaje_liquidacion ?? 0) * countAplicado
      : 0;

  // Auto-select / sync whenever tipoTramite or data changes
  useEffect(() => {
    if (!tarifaUnica) return;

    methods.setValue("tarifa_unica_id", tarifaUnica.id, {
      shouldValidate: false,
    });

    if (especialidades.length > 0) {
      if (grupoA) {
        // All selected, read-only
        const allIds = especialidades.map((e) => e.id);
        methods.setValue("especialidades_seleccionadas", allIds, {
          shouldValidate: true,
        });
      } else {
        // Particulares: SIN preselección — el usuario elige 1, 2 o 3.
        // (El schema exige min 1 para evitar envíos vacíos)
        methods.setValue("especialidades_seleccionadas", [], {
          shouldValidate: true,
        });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tarifaUnica, especialidades, tipoTramite]);

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

  return (
    <div className="space-y-3 rounded-xl border border-primary/20 bg-primary/[0.03] p-4 shadow-sm">
      <div className="flex items-center justify-between gap-2 border-b border-border/40 pb-2">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold uppercase tracking-wide">
            {grupoA ? "Todas las Especialidades" : "Especialidad a aplicar"}
          </h3>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-0.5 text-xs font-bold text-primary">
          <Percent className="h-3 w-3" />
          {formatPercent(totalAplicado)}
          <span className="font-normal text-primary/70">
            × {countAplicado} esp.
          </span>
        </span>
      </div>

      {grupoA ? (
        // ── Group A: rigid all-selected chips (read-only) ──────────────────
        <div className="flex flex-wrap gap-1.5">
          {especialidades.map((esp) => (
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
        </div>
      ) : grupoB ? (
        // ── Group B: checkboxes multi-selection (1, 2 o 3 especialidades) ──
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-foreground">
            Especialidades a aplicar{" "}
            <span className="text-destructive">*</span>
          </legend>
          <div className="flex flex-row flex-wrap gap-2">
            {especialidades.map((esp) => {
              const isSelected = idsSeleccionados.includes(esp.id);
              return (
                <label
                  key={esp.id}
                  className={[
                    "rounded-lg border bg-background px-3 py-2.5 transition-all duration-200 text-left flex-1 min-w-[160px] flex items-center gap-2 cursor-pointer",
                    isSelected
                      ? "border-primary ring-1 ring-primary/30 bg-primary/5"
                      : "border-border hover:border-primary/40",
                  ].join(" ")}
                >
                  <span
                    className={[
                      "flex h-4 w-4 shrink-0 items-center justify-center rounded border",
                      isSelected ? "border-primary" : "border-border",
                    ].join(" ")}
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
                    name="especialidad_por_tipo"
                    className="sr-only"
                    checked={isSelected}
                    onChange={() => {
                      const next = isSelected
                        ? idsSeleccionados.filter((id) => id !== esp.id)
                        : [...idsSeleccionados, esp.id];
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
        // Fallback: sin grupo definido — sin selector
        null
      )}
    </div>
  );
}
